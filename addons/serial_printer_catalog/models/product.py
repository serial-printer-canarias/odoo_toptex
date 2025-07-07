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

        for intento in range(30):
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ JSON no listo. Esperando 30 segundos más... ({intento+1}/30)")
            time.sleep(30)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 15 minutos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

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
                for color in colors:
                    color_name = color.get("colors", {}).get("es", "") or color.get("colorName", "")
                    for size in color.get("sizes", []):
                        talla = size.get("size", "")
                        precio = 0.0
                        if size.get("prices"):
                            precio = float(size["prices"][0].get("price", 0.0))
                        variante = template.product_variant_ids.filtered(
                            lambda v: color_name in v.name and talla in v.name
                        )
                        if variante:
                            variante.standard_price = precio
                            variante.lst_price = round(precio * 1.25, 2)
                            variante.default_code = size.get("sku", "")
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")
        _logger.info(f"🚀 FIN: {creados} plantillas de producto creadas con variantes, color y talla (TopTex).")
        self.sync_variant_images_from_api()
        self.sync_stock_from_api()

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        for template in self.search([('default_code', '!=', False)]):
            default_code = template.default_code
            url = f"{proxy_url}/v3/products?catalog_reference={default_code}&usage_right=b2b_b2c"
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                continue
            data = response.json()[0] if isinstance(response.json(), list) else response.json()
            colors = data.get("colors", [])
            color_images = {}
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                url_img = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                color_images[color_name] = url_img
            for variant in template.product_variant_ids:
                for val in variant.product_template_attribute_value_ids:
                    if val.attribute_id.name.lower() == 'color':
                        img_url = color_images.get(val.name)
                        if img_url:
                            try:
                                image_bin = requests.get(img_url, timeout=30).content
                                variant.image_1920 = image_bin.encode('base64')
                            except:
                                continue

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        for template in self.search([('default_code', '!=', False)]):
            default_code = template.default_code
            inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={default_code}"
            response = requests.get(inv_url, headers=headers)
            if response.status_code != 200:
                continue
            items = response.json().get("items", [])
            for item in items:
                sku = item.get("sku")
                stock = sum([w.get("stock", 0) for w in item.get("warehouses", [])])
                product = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
                if product:
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id.usage', '=', 'internal')
                    ], limit=1)
                    if quant:
                        quant.quantity = stock
                        quant.inventory_quantity = stock

# FIN product.py