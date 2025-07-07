import logging
import requests
import time
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_toptex_batch(self, batch_size=100, max_retries=5, pause_between_batches=5):
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
        for retry in range(max_retries):
            try:
                auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers, timeout=30)
                if auth_response.status_code == 200:
                    break
            except Exception as e:
                _logger.error(f"Intento {retry+1}/{max_retries} autenticando: {e}")
            time.sleep(2)
        else:
            raise UserError(f"❌ Error autenticando tras {max_retries} intentos.")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Bucle de lotes (batch)
        offset = 0
        total_creados = 0
        while True:
            for retry in range(max_retries):
                try:
                    url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&limit={batch_size}&offset={offset}"
                    headers = {
                        "x-api-key": api_key,
                        "x-toptex-authorization": token,
                        "Accept-Encoding": "gzip, deflate, br"
                    }
                    response = requests.get(url, headers=headers, timeout=120)
                    if response.status_code == 200:
                        products_data = response.json()
                        break
                except Exception as e:
                    _logger.error(f"Intento {retry+1}/{max_retries} descargando lote: {e}")
                time.sleep(2)
            else:
                raise UserError(f"❌ Error descargando lote tras {max_retries} intentos en offset {offset}.")

            if not products_data or not isinstance(products_data, list):
                _logger.info("🟢 Todos los productos procesados.")
                break

            # 3. Prepara atributos solo una vez
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            talla_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not talla_attr:
                talla_attr = self.env['product.attribute'].create({'name': 'Talla'})

            creados = 0
            for prod in products_data:
                brand = prod.get("brand", "TopTex")
                name = prod.get("designation", {}).get("es", "Producto sin nombre")
                default_code = prod.get("catalogReference", prod.get("productReference", ""))
                description = prod.get("description", {}).get("es", "")
                colors = prod.get("colors", [])
                all_colors = set()
                all_tallas = set()
                for color in colors:
                    color_name = color.get("colors", {}).get("es", "") or color.get("colorName", "")
                    if color_name: all_colors.add(color_name)
                    for size in color.get("sizes", []):
                        talla = size.get("size", "")
                        if talla: all_tallas.add(talla)
                color_val_objs = []
                for c in all_colors:
                    val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                    color_val_objs.append(val)
                talla_val_objs = []
                for t in all_tallas:
                    val = self.env['product.attribute.value'].search([('name', '=', t), ('attribute_id', '=', talla_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': t, 'attribute_id': talla_attr.id})
                    talla_val_objs.append(val)
                attribute_lines = []
                if color_val_objs:
                    attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_val_objs])]})
                if talla_val_objs:
                    attribute_lines.append({'attribute_id': talla_attr.id, 'value_ids': [(6, 0, [v.id for v in talla_val_objs])]})
                vals = {
                    'name': f"{brand} {name}".strip(),
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
                }
                existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
                if not existe:
                    template = self.create(vals)
                    creados += 1
                    _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")
                else:
                    _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

            total_creados += creados
            _logger.info(f"🚀 Lote terminado. {creados} nuevas plantillas creadas en este batch. Total: {total_creados}")
            if len(products_data) < batch_size:
                break
            offset += batch_size
            time.sleep(pause_between_batches)  # Pausa entre lotes, para evitar sobrecarga

        _logger.info(f"🚀 FIN: {total_creados} plantillas de producto creadas con variantes, color y talla (TopTex).")