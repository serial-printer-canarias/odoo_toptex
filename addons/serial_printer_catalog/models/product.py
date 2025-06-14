import requests
import json
import base64
from io import BytesIO
from PIL import Image
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros de sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            _logger.error("❌ Faltan parámetros de configuración en el sistema.")
            return

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        headers_auth = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload_auth = {
            "username": username,
            "password": password
        }

        response_auth = requests.post(auth_url, headers=headers_auth, json=payload_auth)
        if response_auth.status_code != 200:
            _logger.error(f"❌ Error autenticando: {response_auth.status_code} - {response_auth.text}")
            return

        token = response_auth.json().get("token")
        _logger.info("🟢 Token recibido correctamente.")

        # Obtener datos del producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers_product = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = requests.get(product_url, headers=headers_product)
        if response.status_code != 200:
            _logger.error(f"❌ Error en API producto: {response.status_code} - {response.text}")
            return

        data_list = response.json()
        data = data_list[0] if isinstance(data_list, list) and len(data_list) > 0 else {}
        if not data:
            _logger.error("❌ No se encontró el producto en la respuesta.")
            return

        _logger.info("🟢 JSON interpretado correctamente.")

        # Mapeo de datos
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = data.get("brand", {}).get("name", "").strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # Precios (por ahora fijos)
        list_price = 1.00
        standard_price = 0.00

        # Marca (crear si no existe)
        brand_name = full_name or 'Sin Marca'
        brand_obj = self.env['product.category'].search([('name', '=', brand_name)], limit=1)
        if not brand_obj:
            brand_obj = self.env['product.category'].create({'name': brand_name})

        # Crear plantilla producto
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': brand_obj.id,
        }
        _logger.info(f"🟢 Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"🟢 Plantilla creada: {product_template.name}")

        # Atributos y variantes
        attribute_lines = []

        # Color
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        # Talla
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        for color_data in data.get("colors", []):
            color_name = color_data.get("colors", {}).get("es")
            if not color_name:
                _logger.warning("⚠️ Color vacío, se omite.")
                continue

            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attr.id})

            for size_data in color_data.get("sizes", []):
                size_name = size_data.get("size", {}).get("es")
                if not size_name:
                    _logger.warning("⚠️ Talla vacía, se omite.")
                    continue

                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attr.id})

                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [color_val.id])]
                })
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [size_val.id])]
                })

        if attribute_lines:
            product_template.write({'attribute_line_ids': [(0, 0, line) for line in attribute_lines]})
            _logger.info("🟢 Variantes creadas correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron variantes válidas.")

        # Imagen principal
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = self.get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🟢 Imagen principal asignada desde {img_url}")
                break

        # Imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.id == color_attr.id
            )
            color_name_variant = color_value.name if color_value else None

            color_data_match = next(
                (c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color_name_variant), None)

            if color_data_match:
                images = color_data_match.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = self.get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🟢 Imagen asignada a variante {variant.name} desde {img_url}")
                        break

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image"):
                image = Image.open(BytesIO(response.content))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue())
            else:
                _logger.warning(f"⚠️ Imagen no válida o error al descargar: {url}")
        except Exception as e:
            _logger.error(f"❌ Error al descargar imagen: {e}")
        return None