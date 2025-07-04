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
        file_url = link_response.json().get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Descargar el JSON de productos usando polling (espera hasta 7 minutos)
        max_wait = 420
        wait_time = 10
        total_waited = 0
        products_data = None

        while total_waited < max_wait:
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
            except Exception:
                products_data = None

            if products_data and isinstance(products_data, list) and len(products_data) > 10:
                _logger.info(f"✅ JSON listo con {len(products_data)} productos recibidos tras {total_waited} segundos.")
                break

            _logger.info(f"⌛ JSON no listo. Esperando {wait_time} segundos más...")
            time.sleep(wait_time)
            total_waited += wait_time

        if not products_data or not isinstance(products_data, list):
            raise UserError("❌ El catálogo descargado no es una lista de productos válida.")

        _logger.info(f"🟢 Procesando {len(products_data)} productos TopTex...")

        # Referencias para atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # 4. Procesar y mapear cada producto
        for prod in products_data:
            brand = prod.get("brand", {}).get("name", {}).get("es", "") or "TopTex"
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            variants = []
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("color", {}).get("es", "")
                if color_name:
                    all_colors.add(color_name)
                for size in color.get("sizes", []):
                    size_name = size.get("size")
                    if size_name:
                        all_sizes.add(size_name)

            # Crear valores de atributo color/talla si no existen
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

            # Preparar líneas de atributos para crear variantes
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

            # ¿Ya existe la plantilla? Evitar duplicados por referencia
            existing = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if existing:
                _logger.info(f"⏭️ Plantilla ya existe: {name} [{default_code}]")
                continue

            # Crear la plantilla de producto
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
            _logger.info(f"✅ Creada plantilla {template.name} [{default_code}]")

            # Asignar marca como categoría secundaria si quieres
            brand_categ = self.env['product.category'].search([('name', '=', brand)], limit=1)
            if not brand_categ:
                brand_categ = self.env['product.category'].create({'name': brand})
            template.write({'categ_id': brand_categ.id})

            # Mapear variantes para asignar precio y referencia individual
            for variant in template.product_variant_ids:
                # Color y talla de esta variante
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""

                # Buscar en el JSON la combinación exacta
                for color in colors:
                    if color.get("color", {}).get("es", "") == color_name:
                        for sz in color.get("sizes", []):
                            if sz.get("size") == size_name:
                                # SKU
                                variant.default_code = sz.get("sku", "") or default_code
                                # Precio de coste y venta
                                prices = sz.get("prices", [])
                                if prices:
                                    try:
                                        p_coste = float(prices[0].get("price", 0.0))
                                        variant.standard_price = p_coste
                                        variant.lst_price = round(p_coste * 1.25, 2)  # Margen del 25%
                                    except Exception:
                                        pass

        _logger.info("🎉 Todos los productos y variantes creados correctamente (sin imágenes ni stock).")