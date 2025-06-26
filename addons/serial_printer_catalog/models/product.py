import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api, fields
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
        else:
            _logger.warning(f"⚠️ Imagen no válida: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error imagen {url}: {e}")
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

        # Login para token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # Trae info del producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error obteniendo producto: {response.status_code}")
        data = response.json()
        data = data[0] if isinstance(data, list) and len(data) else data

        # --- Marca y atributos ---
        brand = data.get("brand", {}).get("name", {}).get("es", "")
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # --- Colores y Tallas ---
        colors = data.get("colors", [])
        color_names = [c.get("colors", {}).get("es", "") for c in colors]
        sizes = set()
        for c in colors:
            for sz in c.get("sizes", []):
                sizes.add(sz.get("size"))
        sizes = list(sizes)

        # --- Atributos Odoo ---
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})
        color_vals = {}
        for c in color_names:
            val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
            color_vals[c] = val
        size_vals = {}
        for s in sizes:
            val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
            size_vals[s] = val

        attribute_lines = [
            {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
            {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])},
        ]
        # --- Plantilla ---
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
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # --- Imagen principal ---
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    break

        # --- Precios (precio coste/venta) ---
        price_url = f"{proxy_url}/v3/products/price?catalog_reference=ns300"
        price_headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        price_resp = requests.get(price_url, headers=price_headers)
        price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

        def get_price_cost(color, size):
            for item in price_data:
                if item.get("color") == color and item.get("size") == size:
                    prices = item.get("prices", [])
                    if prices:
                        return float(prices[0].get("price", 0.0))
            return 0.0

        for variant in product_template.product_variant_ids:
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
            size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
            color_name = color_val.name if color_val else ""
            size_name = size_val.name if size_val else ""
            coste = get_price_cost(color_name, size_name)
            variant.standard_price = coste
            variant.lst_price = coste * 1.25 if coste > 0 else 9.8

    # -------- STOCK POR VARIANTE PRO ---------
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales stock.")
            return
        # Token nuevo
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json={"username": username, "password": password}, headers=auth_headers)
        token = auth_response.json().get("token")
        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        inv_resp = requests.get(inventory_url, headers=headers)
        inventory_data = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []
        for variant in self.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "talla").name
            stock = 0
            for item in inventory_data:
                if item.get("color") == color and item.get("size") == size:
                    stock = item.get("stock", 0)
                    break
            # Usa qty_available SOLO si tienes un campo custom, sino usa on_hand, etc.
            variant.qty_available = stock
            _logger.info(f"🟩 Variante: {variant.name} | Stock: {stock}")

    # -------- IMAGENES POR VARIANTE PRO ---------
    def sync_images_by_variant(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales imágenes.")
            return
        # Token nuevo
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json={"username": username, "password": password}, headers=auth_headers)
        token = auth_response.json().get("token")
        product_url = f"{proxy_url}/v3/products?catalog_reference={self.default_code}&usage_right=b2b_b2c"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error("❌ No se pudo obtener producto para imágenes.")
            return
        data = response.json()
        data = data[0] if isinstance(data, list) and len(data) else data
        colors = data.get("colors", [])
        for variant in self.product_variant_ids:
            color_name = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
            color_data = next((c for c in colors if c.get("colors", {}).get("es") == color_name), None)
            if color_data:
                packshots = color_data.get("packshots", {})
                img_url = None
                # FACE > BACK > SIDE
                for key in ["FACE", "BACK", "SIDE"]:
                    if packshots.get(key, {}).get("url_packshot"):
                        img_url = packshots[key]["url_packshot"]
                        break
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🟦 Imagen variante {variant.name} {img_url}")