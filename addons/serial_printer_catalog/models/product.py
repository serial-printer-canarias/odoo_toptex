# coding: utf-8
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
        _logger.info(f"⬝️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {e}")
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
            raise UserError("Faltan credenciales.")

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json=auth_payload, headers=auth_headers).json().get("token")
        if not token:
            raise UserError("Token inválido")

        # Obtener producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        response = requests.get(product_url, headers=headers)
        data = response.json()[0] if response.ok else {}

        name = data.get("designation", {}).get("es", "")
        description = data.get("description", {}).get("es", "")
        code = data.get("catalogReference", "NS300")
        brand = data.get("brand", {}).get("name", {}).get("es", "")

        # Atributos
        colors = data.get("colors", [])
        all_colors = {c.get("colors", {}).get("es", "").strip() for c in colors}
        all_sizes = {s.get("size") for c in colors for s in c.get("sizes", [])}

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        color_vals = {}
        for color in all_colors:
            val = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', color_attr.id)], limit=1)
            color_vals[color] = val or self.env['product.attribute.value'].create({'name': color, 'attribute_id': color_attr.id})

        size_vals = {}
        for size in all_sizes:
            val = self.env['product.attribute.value'].search([('name', '=', size), ('attribute_id', '=', size_attr.id)], limit=1)
            size_vals[size] = val or self.env['product.attribute.value'].create({'name': size, 'attribute_id': size_attr.id})

        # Crear plantilla
        template_vals = {
            'name': name,
            'default_code': code,
            'description_sale': description,
            'type': 'consu',
            'is_storable': True,
            'categ_id': self.env.ref("product.product_category_all").id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
            }), (0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
            })]
        }

        # Optional: marca (si tienes el módulo product_brand)
        BrandModel = self.env['product.brand']
        if BrandModel:
            brand_rec = BrandModel.search([('name', '=', brand)], limit=1)
            if not brand_rec:
                brand_rec = BrandModel.create({'name': brand})
            template_vals['product_brand_id'] = brand_rec.id

        template = self.create(template_vals)

        # Imagen principal
        for img in data.get("images", []):
            if img.get("url_image"):
                template.image_1920 = get_image_binary_from_url(img["url_image"])
                break

        # Inventario y precio
        inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference=ns300"
        price_url = f"{proxy_url}/v3/products/price?catalog_reference=ns300"
        inv_data = requests.get(inv_url, headers=headers).json().get("items", [])
        price_data = requests.get(price_url, headers=headers).json().get("items", [])

        def find_stock(color, size):
            for i in inv_data:
                if i.get("color") == color and i.get("size") == size:
                    return i.get("stock", 0)
            return 0

        def find_cost(color, size):
            for p in price_data:
                if p.get("color") == color and p.get("size") == size:
                    prices = p.get("prices", [])
                    return float(prices[0].get("price", 0.0)) if prices else 0.0
            return 0.0

        for variant in template.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == color_attr).name
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == size_attr).name

            cost = find_cost(color, size)
            stock = find_stock(color, size)
            variant.standard_price = cost
            variant.lst_price = cost * 1.25 if cost else 9.99
            variant.qty_available = stock

            match_color = next((c for c in colors if c.get("colors", {}).get("es", "").strip().lower() == color.lower()), None)
            if match_color:
                img_url = match_color.get("url_image")
                if img_url:
                    variant.image_1920 = get_image_binary_from_url(img_url)

        _logger.info(f"✅ Producto {code} importado correctamente.")