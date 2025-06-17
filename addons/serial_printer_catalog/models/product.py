import requests
import json
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError
from PIL import Image
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # URL de producto por catalog_reference
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"🌐 URL producto: {product_url}")
            _logger.info(f"📡 Headers producto: {headers}")
            _logger.info(f"📥 Respuesta cruda: {response.text}")

            if response.status_code != 200:
                raise UserError(f"❌ Error obteniendo producto: {response.status_code} - {response.text}")

            data = response.json()
            if isinstance(data, list):
                data = data[0]
            elif isinstance(data, dict):
                pass
            else:
                raise UserError("❌ Formato de datos inesperado.")
            _logger.info(f"📦 JSON interpretado: {json.dumps(data, indent=2)}")

            # MAPEO de campos
            name = data.get("translatedName", {}).get("es", "SIN NOMBRE")
            default_code = data.get("catalogReference", "SIN_REF")
            description = data.get("description", {}).get("es", "")
            brand_name = (data.get("brand") or {}).get("name", {}).get("es", "Sin Marca")
            list_price = float(data.get("publicUnitPrice", 0)) if data.get("publicUnitPrice") else 0
            standard_price = float(data.get("purchaseUnitPrice", 0)) if data.get("purchaseUnitPrice") else 0

            # Categoría fija por defecto
            categ_id = self.env['product.category'].search([('name', '=', 'All')], limit=1).id

            # Crear la marca si no existe
            brand = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
            if not brand:
                brand = self.env['product.brand'].create({'name': brand_name})

            # Imagen principal (descargamos desde el proxy si la hay)
            image_url = None
            colors = data.get("colors", [])
            if colors and colors[0].get("visual"):
                image_url = colors[0]["visual"]

            image_1920 = False
            if image_url:
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        img = Image.open(BytesIO(image_response.content))
                        img_buffer = BytesIO()
                        img.save(img_buffer, format='PNG')
                        image_1920 = base64.b64encode(img_buffer.getvalue())
                except Exception as e_img:
                    _logger.warning(f"⚠ Error descargando imagen: {e_img}")

            # Crear producto template
            product_template = self.create({
                'name': name,
                'default_code': default_code,
                'categ_id': categ_id,
                'description_sale': description,
                'list_price': list_price,
                'standard_price': standard_price,
                'image_1920': image_1920,
                'brand_id': brand.id if hasattr(self.env['product.template'], 'brand_id') else False,
                'type': 'product',
            })

            _logger.info(f"✅ Producto creado correctamente: {product_template.name}")

            # Variantes de Color y Talla
            # Atributo Color
            color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attribute:
                color_attribute = self.env['product.attribute'].create({'name': 'Color'})

            color_values = []
            for color in colors:
                color_name = color.get("translatedColorName", {}).get("es", "")
                if not color_name:
                    continue
                value = self.env['product.attribute.value'].search([
                    ('name', '=', color_name),
                    ('attribute_id', '=', color_attribute.id)
                ], limit=1)
                if not value:
                    value = self.env['product.attribute.value'].create({
                        'name': color_name,
                        'attribute_id': color_attribute.id
                    })
                color_values.append(value.id)

            # Atributo Talla
            sizes = data.get("sizes", [])
            size_attribute = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attribute:
                size_attribute = self.env['product.attribute'].create({'name': 'Talla'})

            size_values = []
            for size in sizes:
                size_name = size.get("size", "")
                if not size_name:
                    continue
                value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name),
                    ('attribute_id', '=', size_attribute.id)
                ], limit=1)
                if not value:
                    value = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attribute.id
                    })
                size_values.append(value.id)

            # Asignar atributos al template
            product_template.write({
                'attribute_line_ids': [
                    (0, 0, {
                        'attribute_id': color_attribute.id,
                        'value_ids': [(6, 0, color_values)]
                    }),
                    (0, 0, {
                        'attribute_id': size_attribute.id,
                        'value_ids': [(6, 0, size_values)]
                    })
                ]
            })

            _logger.info("✅ Variantes de producto creadas correctamente.")

        except Exception as e:
            _logger.error(f"❌ Error final procesando producto: {str(e)}")