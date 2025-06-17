import requests
import json
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from PIL import Image
from io import BytesIO

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Obtener datos del producto por catalog_reference
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        product_headers = {
            "x-api-key": api_key,
            "Authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=product_headers)
            _logger.info(f"📡 URL producto: {product_url}")
            _logger.info(f"📡 Headers: {product_headers}")
            _logger.info(f"📡 Respuesta cruda: {response.text}")

            if response.status_code != 200:
                raise UserError(f"❌ Error producto: {response.status_code}")

            product_data = response.json()
            _logger.info(f"📦 JSON recibido: {json.dumps(product_data)}")

        except Exception as e:
            _logger.error(f"❌ Error obteniendo producto: {e}")
            return

        if not isinstance(product_data, dict) or not product_data:
            _logger.error("❌ No se encontraron datos dentro del dict.")
            return

        # Mapping seguro
        name = product_data.get("translatedName", {}).get("es", "SIN NOMBRE")
        default_code = product_data.get("catalogReference", "SIN_REF")
        description = product_data.get("description", {}).get("es", "")
        brand = product_data.get("brand", {}).get("name", {}).get("es", "Sin Marca")
        price_sale = product_data.get("publicUnitPrice", 0.0)
        standard_price = product_data.get("purchaseUnitPrice", 0.0)

        # Buscar o crear marca (como categoría de marca)
        brand_category = self.env['product.category'].search([('name', '=', brand)], limit=1)
        if not brand_category:
            brand_category = self.env['product.category'].create({'name': brand})

        # Procesar imagen principal
        image_url = None
        if product_data.get("images"):
            image_url = product_data["images"][0].get("url", None)

        image_1920 = False
        if image_url:
            try:
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                image_1920 = base64.b64encode(buffer.getvalue())
                _logger.info("🖼 Imagen principal cargada correctamente")
            except Exception as e:
                _logger.warning(f"⚠ Error cargando imagen: {e}")

        # Crear atributos de variantes
        attribute_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not attribute_color:
            attribute_color = self.env['product.attribute'].create({'name': 'Color'})

        attribute_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not attribute_size:
            attribute_size = self.env['product.attribute'].create({'name': 'Talla'})

        # Extraer variantes
        variant_values = []
        for color in product_data.get("colors", []):
            color_name = color.get("translatedName", {}).get("es", "Sin Color")
            color_value = self.env['product.attribute.value'].search(
                [('name', '=', color_name), ('attribute_id', '=', attribute_color.id)], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': attribute_color.id})

            for size in color.get("sizes", []):
                size_name = size.get("size", "Sin Talla")
                size_value = self.env['product.attribute.value'].search(
                    [('name', '=', size_name), ('attribute_id', '=', attribute_size.id)], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': attribute_size.id})

                variant_values.append((color_value, size_value))

        # Crear template con atributos
        template = self.create({
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'categ_id': brand_category.id,
            'list_price': price_sale,
            'standard_price': standard_price,
            'description_sale': description,
            'image_1920': image_1920,
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': attribute_color.id,
                    'value_ids': [(6, 0, [v[0].id for v in variant_values])]
                }),
                (0, 0, {
                    'attribute_id': attribute_size.id,
                    'value_ids': [(6, 0, [v[1].id for v in variant_values])]
                }),
            ]
        })

        _logger.info("✅ Producto creado completamente con variantes.")