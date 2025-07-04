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
    def sync_toptex_products(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("Faltan credenciales de TopTex en los parámetros del sistema.")

        # 1. Login y token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió un token válido.")

        _logger.info("Token recibido correctamente.")

        # 2. Solicitar enlace temporal para descargar el JSON
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        file_url = link_response.json().get('link')
        if not file_url:
            raise UserError("No se recibió un enlace de descarga de catálogo.")

        _logger.info(f"Link temporal de catálogo: {file_url}")

        # 3. Descargar JSON: esperar (retry) hasta que esté listo (máx 7 minutos)
        max_wait = 420   # segundos (7 minutos)
        waited = 0
        sleep_time = 10
        products_data = None

        while waited < max_wait:
            _logger.info(f"Intentando descargar el JSON de productos... (esperado {waited}/{max_wait}s)")
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    _logger.info(f"JSON listo con {len(products_data)} productos recibidos tras {waited} segundos.")
                    break
                else:
                    _logger.info(f"JSON no listo. Esperando {sleep_time} segundos más...")
            except Exception as e:
                _logger.info(f"JSON aún no generado ({str(e)}). Esperando {sleep_time} segundos más...")

            time.sleep(sleep_time)
            waited += sleep_time

        if not (products_data and isinstance(products_data, list)):
            raise UserError("No se pudo descargar el JSON válido de productos TopTex tras esperar el máximo tiempo.")

        _logger.info(f"Procesando {len(products_data)} productos TopTex...")

        # 4. Crear/actualizar atributos Color/Talla si no existen
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # 5. Procesar productos
        for prod in products_data:
            try:
                # Variables principales
                brand = prod.get("brand", {}).get("name", {}).get("es", "") or "TopTex"
                name = prod.get("designation", {}).get("es", "Producto sin nombre")
                default_code = prod.get("catalogReference", prod.get("productReference", ""))
                description = prod.get("description", {}).get("es", "")
                colors = prod.get("colors", [])
                sizes_all = set()
                colors_all = set()

                # 5.1 Reunir todos los valores de color/talla
                for color in colors:
                    color_name = color.get("color", {}).get("es", "")
                    if color_name:
                        colors_all.add(color_name)
                        for sz in color.get("sizes", []):
                            size_name = sz.get("size", "")
                            if size_name:
                                sizes_all.add(size_name)

                # 5.2 Atributos y valores
                color_vals = []
                for c in colors_all:
                    val = self.env['product.attribute.value'].search([
                        ('name', '=', c),
                        ('attribute_id', '=', color_attr.id)
                    ], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                    color_vals.append(val.id)
                size_vals = []
                for s in sizes_all:
                    val = self.env['product.attribute.value'].search([
                        ('name', '=', s),
                        ('attribute_id', '=', size_attr.id)
                    ], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                    size_vals.append(val.id)

                attribute_lines = []
                if color_vals:
                    attribute_lines.append({
                        'attribute_id': color_attr.id,
                        'value_ids': [(6, 0, color_vals)]
                    })
                if size_vals:
                    attribute_lines.append({
                        'attribute_id': size_attr.id,
                        'value_ids': [(6, 0, size_vals)]
                    })

                # 5.3 Crear la plantilla de producto
                template_vals = {
                    'name': f"{brand} {name}".strip(),
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    'list_price': 0.0,
                    'standard_price': 0.0,
                    'brand_id': False  # si tienes tu modelo de marcas
                }
                template = self.env['product.template'].create(template_vals)
                _logger.info(f"Creada plantilla {template.name} [{template.id}]")

                # 5.4 Mapear variantes: coste, venta
                # (Las variantes se crean automáticamente)
                for variant in template.product_variant_ids:
                    # Identificar color/talla
                    color_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == size_attr.id)

                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""

                    # Buscar precios
                    price_cost = 0.0
                    price_sale = 0.0

                    for color in colors:
                        c_name = color.get("color", {}).get("es", "")
                        if c_name == color_name:
                            for sz in color.get("sizes", []):
                                if sz.get("size", "") == size_name:
                                    prices = sz.get("prices", [])
                                    if prices:
                                        price_cost = float(prices[0].get("price", 0.0))
                                        price_sale = price_cost * 1.25
                                    break

                    variant.standard_price = price_cost
                    variant.lst_price = price_sale
                    variant.default_code = default_code
            except Exception as e:
                _logger.warning(f"❌ Error procesando producto: {str(e)}")
        _logger.info("✅ FIN: Productos creados correctamente.")