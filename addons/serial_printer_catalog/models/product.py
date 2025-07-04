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
        # 1. Credenciales desde parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # 2. Autenticación
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

        # 3. Obtener el enlace temporal del catálogo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 4. Descargar el JSON esperando (polling) hasta que esté listo
        json_ready = False
        wait_time = 10
        max_attempts = 50  # Hasta 8-10 minutos máximo
        attempt = 0
        products_data = None
        while not json_ready and attempt < max_attempts:
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list):
                    json_ready = True
                    _logger.info(f"✅ JSON listo con {len(products_data)} productos recibidos tras {attempt * wait_time} segundos.")
                else:
                    _logger.info(f"⏳ JSON no listo. Esperando {wait_time} segundos más…")
                    time.sleep(wait_time)
            except Exception as e:
                _logger.info(f"⏳ JSON no listo (parse error). Esperando {wait_time} segundos más…")
                time.sleep(wait_time)
            attempt += 1
        if not json_ready:
            raise UserError("❌ No se pudo descargar el JSON de productos a tiempo.")

        _logger.info(f"🟢 Procesando {len(products_data)} productos TopTex...")

        # 5. Mapeo y creación de productos (solo variantes, marca, tallas, color, precio venta/coste)
        for prod in products_data:
            # Marca
            brand = prod.get("brand", {}).get("name", {}).get("es", "") or "TopTex"
            # Nombre
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            # Código referencia
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            # Descripción (solo español)
            description = prod.get("description", {}).get("es", "")
            # Colores y tallas
            colors = prod.get("colors", [])

            # Obtener todos los colores/tallas disponibles
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("color", {}).get("es", "")
                if color_name:
                    all_colors.add(color_name)
                    for size in color.get("sizes", []):
                        if size.get("size"):
                            all_sizes.add(size.get("size"))

            # Crear atributos (solo si no existen)
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

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

            # Líneas de atributo para la plantilla
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

            # Plantilla de producto
            template_vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            template = self.env['product.template'].create(template_vals)
            _logger.info(f"✅ Creada plantilla {template.name} [{template.default_code}]")

            # Mapeo variantes
            for variant in template.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""
                # Buscar precios por variante (color/talla)
                found = False
                for color in colors:
                    col_name = color.get("color", {}).get("es", "")
                    if col_name == color_name:
                        for sz in color.get("sizes", []):
                            if sz.get("size") == size_name:
                                # SKU/Referencia única
                                variant.default_code = sz.get("sku", "") or default_code
                                # Precio de coste
                                variant.standard_price = float(sz.get("costPrice", 0.0))
                                # Precio de venta (si tienes info de 'prices', si no lo puedes dejar como coste x margen fijo)
                                variant.lst_price = float(sz.get("costPrice", 0.0)) * 1.35  # ejemplo 35% margen
                                found = True
                                break
                    if found:
                        break

        _logger.info("✅ Sincronización y creación de productos/variantes finalizada (sin imágenes ni stock).")