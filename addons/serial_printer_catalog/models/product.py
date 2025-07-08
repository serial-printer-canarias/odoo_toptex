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
            image = Image.open(io.BytesIO(response.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {str(e)}")
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
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        token = requests.post(auth_url, json={"username": username, "password": password}, headers={
            "x-api-key": api_key, "Content-Type": "application/json"
        }).json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # Búsqueda atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # Paginación catálogo
        page = 0
        while True:
            url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&limit=50&page={page}"
            headers = {"x-api-key": api_key, "x-toptex-authorization": token}
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                _logger.error(f"❌ Error en página {page}: {resp.text}")
                break
            products = resp.json()
            if not products:
                break

            for data in products:
                brand_data = data.get("brand", {})
                brand = brand_data.get("name", {}).get("es", "Sin marca")
                name = data.get("designation", {}).get("es", "Sin nombre")
                description = data.get("description", {}).get("es", "")
                default_code = data.get("catalogReference", "")
                full_name = f"{brand} {name}".strip()

                # Colores y tallas
                colors = data.get("colors", [])
                all_colors = set()
                all_sizes = set()
                for color in colors:
                    cname = color.get("colors", {}).get("es", "")
                    all_colors.add(cname)
                    for size in color.get("sizes", []):
                        all_sizes.add(size.get("size"))

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
                    {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                    {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]},
                ]

                # Crear plantilla
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
                images = data.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            template.image_1920 = image_bin
                            break

                # Precios
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={default_code}"
                price_data = []
                try:
                    price_resp = requests.get(price_url, headers=headers)
                    price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []
                except Exception as e:
                    _logger.error(f"❌ Error precio: {e}")

                def get_price(color, size):
                    for item in price_data:
                        if item.get("color") == color and item.get("size") == size:
                            prices = item.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                # SKU
                inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={default_code}"
                inventory_data = []
                try:
                    inv_resp = requests.get(inventory_url, headers=headers)
                    inventory_data = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []
                except Exception as e:
                    _logger.error(f"❌ Error inventario: {e}")

                def get_sku(color, size):
                    for item in inventory_data:
                        if item.get("color") == color and item.get("size") == size:
                            return item.get("sku")
                    return ""

                for variant in template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                    color = color_val.name if color_val else ""
                    size = size_val.name if size_val else ""
                    sku = get_sku(color, size)
                    price = get_price(color, size)
                    variant.default_code = sku
                    variant.standard_price = price
                    variant.lst_price = price * 1.25 if price > 0 else 9.9
                    _logger.info(f"✅ Variante {variant.name}: {sku} | €{price}")

            page += 1
        _logger.info("🎯 Catálogo general cargado correctamente.")

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        token = requests.post(f"{proxy_url}/v3/authenticate", json={"username": username, "password": password}, headers={
            "x-api-key": api_key, "Content-Type": "application/json"
        }).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        inventory_url = f"{proxy_url}/v3/products/inventory/all"
        inv_resp = requests.get(inventory_url, headers=headers)
        if inv_resp.status_code != 200:
            _logger.error("❌ Error al obtener inventario: " + inv_resp.text)
            return
        items = inv_resp.json().get("items", [])
        StockQuant = self.env['stock.quant']
        for item in items:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            variant = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if variant:
                quant = StockQuant.search([('product_id', '=', variant.id), ('location_id.usage', '=', 'internal')], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    _logger.warning(f"⚠️ No se encontró stock.quant para {sku}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        token = requests.post(f"{proxy_url}/v3/authenticate", json={"username": username, "password": password}, headers={
            "x-api-key": api_key, "Content-Type": "application/json"
        }).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        page = 0
        while True:
            url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&limit=50&page={page}"
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                break
            products = resp.json()
            if not products:
                break
            for data in products:
                colors = data.get("colors", [])
                color_imgs = {
                    c.get("colors", {}).get("es", ""): c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                    for c in colors
                }
                catalog_ref = data.get("catalogReference")
                variants = self.env['product.template'].search([
                    '|', ('default_code', '=', catalog_ref), ('name', 'ilike', catalog_ref)
                ]).product_variant_ids
                for variant in variants:
                    color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color').name
                    img_url = color_imgs.get(color)
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🖼️ Imagen FACE asignada a {variant.default_code}")
            page += 1