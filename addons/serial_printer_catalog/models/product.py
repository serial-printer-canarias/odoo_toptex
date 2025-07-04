import json
import logging
import requests
import time
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

        # 1. Autenticación y token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Obtener el enlace temporal del catálogo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        file_url = link_response.json().get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Esperar hasta que el JSON esté listo y descargar (máx 7 minutos)
        products_data = []
        for _ in range(30):  # 30 intentos cada 14s = 7 minutos
            file_response = requests.get(file_url, headers=headers)
            if file_response.status_code == 200:
                try:
                    json_data = file_response.json()
                    if isinstance(json_data, dict) and 'items' in json_data:
                        products_data = json_data['items']
                    elif isinstance(json_data, list):
                        products_data = json_data
                    if products_data: break
                except Exception as e:
                    _logger.warning(f"⏳ Esperando a que el JSON esté listo: {str(e)}")
            time.sleep(14)
        else:
            raise UserError("❌ El archivo JSON de productos no estuvo listo a tiempo.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos.")

        # 4. Crear atributos si no existen (Color, Talla)
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # 5. Crear productos y variantes (solo los campos básicos)
        for prod in products_data:
            # Mapeo NS300 style
            name = prod.get("designation", {}).get("es", "Sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])

            # Extraer colores/tallas
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                if color_name: all_colors.add(color_name)
                for sz in color.get("sizes", []):
                    size_name = sz.get("size")
                    if size_name: all_sizes.add(size_name)

            # Crear valores de atributo si faltan
            color_vals = {}
            for c in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals[c] = val
            size_vals = {}
            for s in all_sizes:
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                size_vals[s] = val

            attribute_lines = []
            if all_colors:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                })
            if all_sizes:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                })

            template_vals = {
                'name': name,
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            template = self.create(template_vals)

            # Mapear variantes: SKU y precio (ejemplo simple)
            for variant in template.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""
                for c in colors:
                    col_name = c.get("colors", {}).get("es", "")
                    if col_name == color_name:
                        for sz in c.get("sizes", []):
                            if sz.get("size") == size_name:
                                variant.default_code = sz.get("sku", "")
                                # Puedes añadir precio aquí si lo necesitas

        _logger.info("✅ Creación de productos y variantes finalizada (sin imágenes ni stock).")