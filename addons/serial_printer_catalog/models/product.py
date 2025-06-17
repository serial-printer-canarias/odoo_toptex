import requests
import json
import base64
import logging
from io import BytesIO
from PIL import Image
from odoo import models, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        IrConfig = self.env['ir.config_parameter'].sudo()
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')
        proxy_url = IrConfig.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan parámetros de configuración.")
            return

        # Autenticación: obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            auth_response.raise_for_status()
            token = auth_response.json().get("token")
            if not token:
                _logger.error("❌ No se obtuvo token de autenticación.")
                return
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando: {e}")
            return

        # Obtener producto NS300
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        product_headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {token}",
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=product_headers)
            _logger.info(f"➡ URL de producto: {product_url}")
            _logger.info(f"➡ Respuesta: {response.text}")
            response.raise_for_status()
            product_data = response.json()
        except Exception as e:
            _logger.error(f"❌ Error obteniendo producto: {e}")
            return

        if not product_data or not isinstance(product_data, dict):
            _logger.error("❌ Respuesta vacía o malformada.")
            return

        _logger.info("📦 JSON principal recibido correctamente.")

        # MAPPEO DATOS GENERALES
        translated_name = product_data.get("translatedName", {}).get("es", "SIN NOMBRE")
        default_code = product_data.get("catalogReference", "SIN_REF")
        description = product_data.get("description", {}).get("es", "")
        brand_name = (product_data.get("brand") or {}).get("name", {}).get("es", "Sin Marca")
        list_price = product_data.get("publicUnitPrice", 0.0)
        standard_price = product_data.get("purchaseUnitPrice", 0.0)

        # Procesar imagen principal
        image_1920 = False
        images = product_data.get("images", [])
        if images:
            image_url = images[0].get("url")
            try:
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                image_1920 = base64.b64encode(buffer.getvalue())
                _logger.info("🖼 Imagen principal procesada correctamente.")
            except Exception as e:
                _logger.warning(f"⚠ Error procesando imagen: {e}")

        # Buscar o crear categoría
        category = self.env['product.category'].search([('name', '=', 'TopTex')], limit=1)
        if not category:
            category = self.env['product.category'].create({'name': 'TopTex'})

        # Buscar o crear marca
        brand_obj = self.env['product.category'].search([('name', '=', brand_name)], limit=1)
        if not brand_obj:
            brand_obj = self.env['product.category'].create({'name': brand_name})

        # CREAR PRODUCT TEMPLATE BASE
        template_vals = {
            'name': translated_name,
            'default_code': default_code,
            'categ_id': brand_obj.id,
            'description_sale': description,
            'type': 'product',
            'list_price': list_price,
            'standard_price': standard_price,
            'sale_ok': True,
            'purchase_ok': True,
            'image_1920': image_1920,
        }

        product_template = self.create(template_vals)
        _logger.info(f"✅ Producto template creado: {translated_name}")

        # VARIANTES COLOR Y TALLA
        attribute_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not attribute_color:
            attribute_color = self.env['product.attribute'].create({'name': 'Color'})

        attribute_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not attribute_size:
            attribute_size = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in product_data.get("colors", []):
            color_name = color.get("translatedName", {}).get("es", "Sin Color")
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name),
                ('attribute_id', '=', attribute_color.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': attribute_color.id
                })
            color_values.append(color_val.id)

            for size in color.get("sizes", []):
                size_name = size.get("size", "Sin Talla")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name),
                    ('attribute_id', '=', attribute_size.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': attribute_size.id
                    })
                size_values.append(size_val.id)

        # Asignación de variantes al producto template
        product_template.write({
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': attribute_color.id,
                    'value_ids': [(6, 0, color_values)]
                }),
                (0, 0, {
                    'attribute_id': attribute_size.id,
                    'value_ids': [(6, 0, size_values)]
                })
            ]
        })

        _logger.info("✅ Variantes de color y talla asignadas correctamente.")
        _logger.info("✅ Sincronización de NS300 finalizada con éxito.")