import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_json_from_link(url):
    r = requests.get(url, timeout=30)
    if r.status_code == 200:
        return r.json()
    raise UserError(f"Error descargando fichero: {url}")

def get_image_binary_from_url(url):
    try:
        resp = requests.get(url, stream=True, timeout=10)
        if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(resp.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"Error descargando imagen: {url} -> {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_catalog_all(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token TopTex")
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}

        # 1. Descargar catálogo (enlace S3)
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        resp = requests.get(catalog_url, headers=headers)
        file_link = resp.json().get("link")
        if not file_link:
            raise UserError("No se recibió el link del fichero catálogo")
        catalog = get_json_from_link(file_link)

        # 2. Descargar precios MASIVO (enlace S3)
        price_url = f"{proxy_url}/v3/products/price?result_in_file=1"
        resp_price = requests.get(price_url, headers=headers)
        file_link_price = resp_price.json().get("link")
        prices_json = get_json_from_link(file_link_price)
        # Prepara diccionario rápido SKU -> price
        sku_price_map = {}
        for item in prices_json.get("items", []):
            sku = item.get("sku")
            price = float(item.get("prices", [{}])[0].get("price", 0.0)) if item.get("prices") else 0.0
            sku_price_map[sku] = price

        for prod in catalog:
            catalog_ref = prod.get("catalogReference", "")
            brand = prod.get("brand", {}).get("name", {}).get("es", "")
            name = prod.get("designation", {}).get("es", "")
            description = prod.get("description", {}).get("es", "")
            images = prod.get("images", [])
            colors = prod.get("colors", [])
            if not catalog_ref or not name:
                continue

            # Marca
            brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_obj and brand:
                brand_obj = self.env['product.brand'].create({'name': brand})

            # Atributos
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

            color_vals, size_vals = {}, {}
            all_colors, all_sizes = set(), set()
            for c in colors:
                color_name = c.get("colors", {}).get("es", "")
                all_colors.add(color_name)
                for sz in c.get("sizes", []):
                    all_sizes.add(sz.get("size"))
            for c in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals[c] = val
            for s in all_sizes:
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                size_vals[s] = val

            attribute_lines = [
                {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]}
            ]

            # Plantilla
            template = self.env['product.template'].search([('default_code', '=', catalog_ref)], limit=1)
            if not template:
                template = self.create({
                    'name': f"{brand} {name}",
                    'default_code': catalog_ref,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
                    'product_brand_id': brand_obj.id if brand_obj else False,
                })
            # Imagen principal
            for img in images:
                img_url = img.get("url_image", "")
                if img_url:
                    template.image_1920 = get_image_binary_from_url(img_url)
                    break

            # Asigna coste y precio de venta a variantes al CREARLAS (como en NS300)
            for variant in template.product_variant_ids:
                sku = variant.default_code
                coste = sku_price_map.get(sku, 0.0)
                variant.standard_price = coste
                variant.lst_price = coste * 1.25 if coste else 9.8

        _logger.info("✅ Catálogo TopTex sincronizado TODO (productos, variantes, precios coste)")

    # ==== SERVER ACTION PARA STOCK ====
    def sync_toptex_stock_all(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}

        # Descarga inventario (enlace S3)
        inv_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        resp = requests.get(inv_url, headers=headers)
        link = resp.json().get("link")
        inventory = get_json_from_link(link)
        inventory_items = inventory.get("items", []) if isinstance(inventory, dict) else inventory

        StockQuant = self.env['stock.quant']
        ProductProduct = self.env['product.product']

        for item in inventory_items:
            sku = item.get("sku")
            stock = sum([w.get("stock", 0) for w in item.get("warehouses", [])])
            product = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if product:
                quant = StockQuant.search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal')], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"Stock.quant actualizado: {sku} = {stock}")
                else:
                    # Si no existe stock.quant lo crea
                    location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                    if location:
                        StockQuant.create({'product_id': product.id, 'location_id': location.id, 'quantity': stock, 'inventory_quantity': stock})
                        _logger.info(f"Stock.quant creado para {sku} = {stock}")
            else:
                _logger.warning(f"Variante no encontrada para SKU {sku}")

    # ==== SERVER ACTION PARA IMÁGENES VARIANTES ====
    def sync_toptex_variant_images_all(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}

        # Descarga catálogo (enlace S3)
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        resp = requests.get(catalog_url, headers=headers)
        file_link = resp.json().get("link")
        catalog = get_json_from_link(file_link)

        ProductProduct = self.env['product.product']
        for prod in catalog:
            colors = prod.get("colors", [])
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                img_url = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for sz in color.get("sizes", []):
                    sku = sz.get("sku")
                    product = ProductProduct.search([('default_code', '=', sku)], limit=1)
                    if product and img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product.image_1920 = image_bin
                            _logger.info(f"Imagen variante asignada a {sku}")