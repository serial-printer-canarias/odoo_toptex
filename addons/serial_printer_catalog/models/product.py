import json
import logging
import requests
from odoo import models, api
from odoo.exceptions import UserError

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

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
        data_list = response.json()
        data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}

        # Mapeo base
        brand = data.get("brand", {}).get("name", {}).get("es", "")
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = 9.8
        standard_price = 0.0

        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    standard_price = float(price_str)
                    break
                except Exception:
                    continue
            if standard_price:
                break

        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }

        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Variantes
        attribute_lines = []
        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            for size in color.get("sizes", []):
                size_name = size.get("size")

                color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
                color_val = self.env['product.attribute.value'].search([('name', '=', color_name), ('attribute_id', '=', color_attr.id)], limit=1) or self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attr.id})

                size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})
                size_val = self.env['product.attribute.value'].search([('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1) or self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attr.id})

                if all(line['attribute_id'] != color_attr.id for line in attribute_lines):
                    attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [color_val.id])]})
                if all(line['attribute_id'] != size_attr.id for line in attribute_lines):
                    attribute_lines.append({'attribute_id': size_attr.id, 'value_ids': [(6, 0, [size_val.id])]})

        if attribute_lines:
            product_template.write({'attribute_line_ids': [(0, 0, line) for line in attribute_lines]})
            _logger.info("✅ Atributos y valores asignados correctamente.")

        # Imagen principal
        for img in data.get("images", []):
            url = img.get("url_image", "")
            if url.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    img_response = requests.get(url)
                    if img_response.ok and "image" in img_response.headers.get("Content-Type", ""):
                        product_template.image_1920 = img_response.content
                        _logger.info(f"🖼️ Imagen principal asignada: {url}")
                        break
                except Exception as e:
                    _logger.warning(f"⚠️ Error asignando imagen principal desde {url}: {e}")

        # Imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_name = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == "Color").name
            color_data = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color_name), None)
            variant_url = color_data.get("url_image") if color_data else None
            if variant_url:
                try:
                    res = requests.get(variant_url)
                    if res.ok and "image" in res.headers.get("Content-Type", ""):
                        variant.image_1920 = res.content
                        _logger.info(f"🖼️ Imagen variante asignada: {variant.name}")
                except Exception as e:
                    _logger.warning(f"⚠️ Error cargando imagen variante {variant.name}: {e}")