# -*- coding: utf-8 -*-
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
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"❌ Error imagen desde {url}: {str(e)}")
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
            raise UserError("❌ Parámetros de API incompletos")

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=auth_headers)
        token = token_resp.json().get("token")
        if not token:
            raise UserError("❌ Token inválido")

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        page = 0
        while True:
            paginated_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&limit=50&page={page}"
            response = requests.get(paginated_url, headers=headers)
            if response.status_code != 200:
                _logger.warning(f"❌ Error página {page}: {response.text}")
                break
            products = response.json()
            if not products:
                break

            for data in products:
                brand = data.get("brand", {}).get("name", {}).get("es", "") or "Marca desconocida"
                name = data.get("designation", {}).get("es", "Producto sin nombre")
                default_code = data.get("catalogReference", "NOREF")
                description = data.get("description", {}).get("es", "")
                full_name = f"{brand} {name}".strip()

                colors = data.get("colors", [])
                all_sizes = set()
                all_colors = set()
                for color in colors:
                    all_colors.add(color.get("colors", {}).get("es", ""))
                    for s in color.get("sizes", []):
                        all_sizes.add(s.get("size"))

                color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
                size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

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

                attribute_lines = [
                    {
                        'attribute_id': color_attr.id,
                        'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                    },
                    {
                        'attribute_id': size_attr.id,
                        'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                    }
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

                product_template = self.create(template_vals)

                for img in data.get("images", []):
                    img_url = img.get("url_image")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product_template.image_1920 = image_bin
                            break

            page += 1

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = token_resp.json().get("token")
        if not token:
            _logger.error("❌ Token inválido (stock)")
            return

        headers["x-toptex-authorization"] = token
        stock_url = f"{proxy_url}/v3/products/inventory/all"
        response = requests.get(stock_url, headers=headers)
        items = response.json().get("items", []) if response.status_code == 200 else []

        StockQuant = self.env['stock.quant']
        for item in items:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if product:
                quant = StockQuant.search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal')], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"📦 Stock actualizado {sku}: {stock}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = token_resp.json().get("token")
        if not token:
            _logger.error("❌ Token inválido (imágenes)")
            return

        headers["x-toptex-authorization"] = token
        page = 0
        while True:
            url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&limit=50&page={page}"
            response = requests.get(url, headers=headers)
            products = response.json() if response.status_code == 200 else []
            if not products:
                break

            for data in products:
                default_code = data.get("catalogReference", "")
                colors = data.get("colors", [])
                color_images = {
                    c.get("colors", {}).get("es", ""): c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                    for c in colors
                }

                template = self.search([
                    '|', ('default_code', '=', default_code), ('name', 'ilike', default_code)
                ], limit=1)
                if not template:
                    continue

                for variant in template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                    img_url = color_images.get(color_val.name if color_val else "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🖼️ Imagen FACE {variant.default_code}")

            page += 1