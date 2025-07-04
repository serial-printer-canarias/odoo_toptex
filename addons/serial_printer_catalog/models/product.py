import json
import logging
import requests
from odoo import models, api
from odoo.exceptions import UserError
import time

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def create_products_toptex(self):
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

        # 3. Esperar a que el archivo esté generado (máx 10 minutos)
        max_wait = 600  # 10 min
        sleep_time = 30
        elapsed = 0
        while elapsed < max_wait:
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if "items" in products_data and isinstance(products_data["items"], list) and products_data["items"]:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ Esperando generación del JSON ({elapsed}s)...")
            time.sleep(sleep_time)
            elapsed += sleep_time
        else:
            raise UserError("❌ El archivo JSON de productos no estuvo listo tras 10 minutos.")

        _logger.info(f"💾 JSON DE PRODUCTOS RECIBIDO ({len(products_data['items'])} productos)")

        # --- Atributos de producto
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # --- Crear productos
        for prod in products_data["items"]:
            brand = prod.get("brand", "") or "TopTex"
            name = prod.get("designation", {}).get("es") or prod.get("designation", {}).get("en") or "Producto"
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                all_colors.add(color_name)
                for size in color.get("sizes", []):
                    all_sizes.add(size.get("size"))

            # Crear valores de atributo si no existen
            color_vals = {}
            for c in all_colors:
                if not c:
                    continue
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals[c] = val
            size_vals = {}
            for s in all_sizes:
                if not s:
                    continue
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                size_vals[s] = val

            attribute_lines = []
            if color_vals:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                })
            if size_vals:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                })

            # Evitar duplicados
            existing = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if existing:
                continue

            template_vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                'list_price': 0.0,   # se pondrá por variante
                'standard_price': 0.0,  # se pondrá por variante
            }
            template = self.create(template_vals)

            # Crear variantes con precios
            for color in colors:
                color_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                for size in color.get("sizes", []):
                    size_name = size.get("size")
                    # Buscar variante (odoo la crea automáticamente al asignar líneas de atributo)
                    variant = template.product_variant_ids.filtered(
                        lambda v: 
                            color_name in v.product_template_attribute_value_ids.mapped('name') and 
                            size_name in v.product_template_attribute_value_ids.mapped('name')
                    )
                    if not variant:
                        continue
                    # SKU
                    variant.default_code = size.get("sku", "") or ""
                    # Precios
                    price_items = size.get("prices", [])
                    if price_items:
                        variant.standard_price = float(price_items[0].get("price", 0.0))
                        variant.lst_price = float(price_items[0].get("price", 0.0)) * 1.25

        _logger.info("✅ Productos y variantes TopTex creados correctamente.")