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
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            _logger.info(f"✅ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
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

        # --- Autenticación ---
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

        # --- Llamada por lotes de 50 productos ---
        page = 0
        while True:
            product_url = f"{proxy_url}/v3/products/all?limit=50&page={page}"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "Accept-Encoding": "gzip, deflate, br"
            }
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                _logger.error(f"❌ Error página {page}: {response.status_code} - {response.text}")
                break
            products = response.json()
            if not products:
                _logger.info("✅ Catálogo finalizado.")
                break

            for data in products:
                try:
                    # --- MARCA ---
                    brand = data.get("brand", {}).get("name", {}).get("es", "TopTex")
                    name = data.get("designation", {}).get("es", "Producto sin nombre")
                    description = data.get("description", {}).get("es", "")
                    default_code = data.get("catalogReference", "")

                    full_name = f"{brand} {name}".strip()

                    # --- Variantes ---
                    colors = data.get("colors", [])
                    all_colors = set()
                    all_sizes = set()
                    for color in colors:
                        cname = color.get("colors", {}).get("es", "")
                        all_colors.add(cname)
                        for size in color.get("sizes", []):
                            all_sizes.add(size.get("size"))

                    color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
                    size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

                    def get_vals(attr, values):
                        val_dict = {}
                        for v in values:
                            rec = self.env['product.attribute.value'].search([('name', '=', v), ('attribute_id', '=', attr.id)], limit=1)
                            if not rec:
                                rec = self.env['product.attribute.value'].create({'name': v, 'attribute_id': attr.id})
                            val_dict[v] = rec
                        return val_dict

                    color_vals = get_vals(color_attr, all_colors)
                    size_vals = get_vals(size_attr, all_sizes)

                    attribute_lines = [
                        {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                        {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]},
                    ]

                    # --- Crear producto ---
                    product_template = self.create({
                        'name': full_name,
                        'default_code': default_code,
                        'type': 'consu',
                        'is_storable': True,
                        'description_sale': description,
                        'categ_id': self.env.ref("product.product_category_all").id,
                        'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    })

                    # --- Imagen principal ---
                    images = data.get("images", [])
                    for img in images:
                        img_url = img.get("url_image", "")
                        if img_url:
                            image_bin = get_image_binary_from_url(img_url)
                            if image_bin:
                                product_template.image_1920 = image_bin
                                break

                    # --- STOCK e inventario ---
                    inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={default_code}"
                    inv_resp = requests.get(inventory_url, headers=headers)
                    inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                    def get_sku(color, size):
                        for item in inventory_items:
                            if item.get("color") == color and item.get("size") == size:
                                return item.get("sku"), sum(w.get("stock", 0) for w in item.get("warehouses", []))
                        return "", 0

                    # --- Precios ---
                    price_url = f"{proxy_url}/v3/products/price?catalog_reference={default_code}"
                    price_resp = requests.get(price_url, headers=headers)
                    price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                    def get_price(color, size):
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
                        sku, stock = get_sku(color_name, size_name)
                        variant.default_code = sku
                        variant.standard_price = get_price(color_name, size_name)
                        variant.lst_price = variant.standard_price * 1.25 if variant.standard_price > 0 else 9.8

                        self.env['stock.quant'].create({
                            'product_id': variant.id,
                            'location_id': self.env.ref('stock.stock_location_stock').id,
                            'quantity': stock,
                            'inventory_quantity': stock,
                        })

                    _logger.info(f"✅ Producto {default_code} creado correctamente.")
                except Exception as e:
                    _logger.error(f"❌ Error procesando producto: {e}")

            page += 1