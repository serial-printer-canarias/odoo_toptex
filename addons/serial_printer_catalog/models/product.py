# CODIGO COMPLETO COPIABLE PRO PRO
# product.py con productos por paginación + Server Actions separadas

# ⬇️ PÉGALO DIRECTAMENTE EN TU ARCHIVO MODELO

import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"Error imagen {url}: {e}")
    return None

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
            raise UserError("Faltan parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió un token válido.")

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        page = 0
        while True:
            url = f"{proxy_url}/v3/products/all?limit=50&page={page}&usage_right=b2b_b2c"
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                break
            products = response.json()
            if not products:
                break

            for data in products:
                try:
                    brand_data = data.get("brand") or {}
                    brand = brand_data.get("name", {}).get("es") or "Marca desconocida"
                    name = data.get("designation", {}).get("es", "Sin nombre")
                    full_name = f"{brand} {name}"
                    default_code = data.get("catalogReference", "")
                    description = data.get("description", {}).get("es", "")

                    colors = data.get("colors", [])
                    all_colors = set()
                    all_sizes = set()
                    for color in colors:
                        cname = color.get("colors", {}).get("es", "")
                        all_colors.add(cname)
                        for s in color.get("sizes", []):
                            all_sizes.add(s.get("size"))

                    color_attr = self.env['product.attribute'].search([('name','=','Color')],limit=1)
                    if not color_attr:
                        color_attr = self.env['product.attribute'].create({'name': 'Color'})
                    size_attr = self.env['product.attribute'].search([('name','=','Talla')],limit=1)
                    if not size_attr:
                        size_attr = self.env['product.attribute'].create({'name': 'Talla'})

                    color_vals = {}
                    for c in all_colors:
                        val = self.env['product.attribute.value'].search([('name','=',c),('attribute_id','=',color_attr.id)], limit=1)
                        if not val:
                            val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                        color_vals[c] = val

                    size_vals = {}
                    for s in all_sizes:
                        val = self.env['product.attribute.value'].search([('name','=',s),('attribute_id','=',size_attr.id)], limit=1)
                        if not val:
                            val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                        size_vals[s] = val

                    attribute_lines = [
                        {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                        {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]},
                    ]

                    template_vals = {
                        'name': full_name,
                        'default_code': default_code,
                        'type': 'consu',
                        'is_storable': True,
                        'description_sale': description,
                        'categ_id': self.env.ref("product.product_category_all").id,
                        'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    }
                    template = self.create(template_vals)

                    # Imagen principal
                    for img in data.get("images", []):
                        url_img = img.get("url_image")
                        if url_img:
                            image_bin = get_image_binary_from_url(url_img)
                            if image_bin:
                                template.image_1920 = image_bin
                                break

                    # PRECIOS
                    try:
                        price_url = f"{proxy_url}/v3/products/price?catalog_reference={default_code}"
                        price_resp = requests.get(price_url, headers=headers)
                        price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []
                    except:
                        price_data = []

                    def get_price(color, size):
                        for item in price_data:
                            if item.get("color") == color and item.get("size") == size:
                                prices = item.get("prices", [])
                                if prices:
                                    return float(prices[0].get("price", 0.0))
                        return 0.0

                    for variant in template.product_variant_ids:
                        cval = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                        sval = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                        cname = cval.name if cval else ""
                        sname = sval.name if sval else ""
                        cost = get_price(cname, sname)
                        variant.standard_price = cost
                        variant.lst_price = cost * 1.25 if cost > 0 else 9.9

                except Exception as e:
                    _logger.error(f"❌ Error al crear producto: {e}")

            page += 1

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(f"{proxy_url}/v3/authenticate", json={"username": username, "password": password}, headers=headers).json().get("token")
        headers.update({"x-toptex-authorization": token})
        inv = requests.get(f"{proxy_url}/v3/products/inventory/all", headers=headers).json().get("items", [])

        for item in inv:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            variant = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if variant:
                quant = self.env['stock.quant'].search([('product_id', '=', variant.id), ('location_id.usage', '=', 'internal')], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"Stock actualizado: {sku} = {stock}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(f"{proxy_url}/v3/authenticate", json={"username": username, "password": password}, headers=headers).json().get("token")
        headers.update({"x-toptex-authorization": token})
        url = f"{proxy_url}/v3/products/all?limit=500&page=0&usage_right=b2b_b2c"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return

        for data in resp.json():
            colors = data.get("colors", [])
            catalog = data.get("catalogReference", "")
            template = self.env['product.template'].search([('default_code', '=', catalog)], limit=1)
            if not template:
                continue
            color_map = {
                c.get("colors", {}).get("es", ""): c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for c in colors
            }
            for variant in template.product_variant_ids:
                val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                name = val.name if val else ""
                url_img = color_map.get(name)
                if url_img:
                    image_bin = get_image_binary_from_url(url_img)
                    if image_bin:
                        variant.image_1920 = image_bin