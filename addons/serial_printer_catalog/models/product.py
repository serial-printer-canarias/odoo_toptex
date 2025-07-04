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

        # 1. Autenticación
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

        # 2. Petición para obtener el enlace temporal de productos
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Esperar hasta que el JSON esté listo y descargar (hasta 7 minutos)
        import time
        for intento in range(30):  # Hasta 7 minutos de espera (14 s * 30 = 420 s)
            file_response = requests.get(file_url, headers=headers)
            if file_response.status_code == 200:
                try:
                    products_data = file_response.json()
                    if isinstance(products_data, dict) and 'items' in products_data:
                        products_data = products_data['items']
                    if isinstance(products_data, list) and products_data:
                        break
                except Exception as e:
                    pass  # El archivo todavía no está disponible, reintentamos
            time.sleep(14)
        else:
            raise UserError("❌ El archivo JSON de productos no estuvo listo a tiempo. Intenta de nuevo más tarde.")

        _logger.info(f"💾 RESPUESTA CRUDA DEL JSON DE PRODUCTOS: {len(products_data)} productos recibidos.")

        # 4. CREACIÓN SOLO DE PLANTILLAS Y VARIANTES (sin imágenes aún)
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        for prod in products_data:
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            brand = prod.get("brand", "TopTex")
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                all_colors.add(color_name)
                for sz in color.get("sizes", []):
                    all_sizes.add(sz.get("size"))

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
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            template = self.create(template_vals)

            # Mapear variantes: SKU y precio
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
                                prices = sz.get("prices", [])
                                if prices:
                                    variant.standard_price = float(prices[0].get("price", 0.0))
                                    variant.lst_price = float(prices[0].get("price", 0.0)) * 1.25

        _logger.info("✅ Sincronización completa de plantillas y variantes TopTex.")