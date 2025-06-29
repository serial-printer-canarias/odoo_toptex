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

        # Autenticación
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

        # Descarga info producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
        data_list = response.json()
        data = data_list[0] if isinstance(data_list, list) and data_list else data_list if isinstance(data_list, dict) else {}

        # --- MARCA ---
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
        if not brand:
            brand = "Native Spirit"

        # --- PLANTILLA PRINCIPAL ---
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        catalog_ref = data.get("catalogReference", "NS300")
        default_code = catalog_ref

        # --- VARIANTES ---
        colors = data.get("colors", [])
        all_sizes = set()
        all_colors = set()
        for color in colors:
            color_name = color.get("colors", {}).get("es", "")
            all_colors.add(color_name)
            for size in color.get("sizes", []):
                all_sizes.add(size.get("size"))

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

        # PLANTILLA PRINCIPAL: default_code SIEMPRE PUESTO
        template_vals = {
            'name': full_name,
            'default_code': default_code,   # <--- AQUI EL CAMPO INTERNO PRINCIPAL!
            'type': 'consu',
            'is_storable': True,
            'description_sale': description,
            'categ_id': self.env.ref("product.product_category_all").id,
            'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
        }
        product_template = self.create(template_vals)

        # Imagen principal
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    break

        # --- BLOQUE INVENTARIO PARA ASIGNAR SKU CORRECTO A VARIANTES ---
        try:
            inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference=ns300"
            inv_resp = requests.get(inventory_url, headers=headers)
            inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []
        except Exception as e:
            _logger.error(f"❌ Error al obtener inventario: {e}")
            inventory_items = []

        def get_sku(color, size):
            for item in inventory_items:
                if item.get("color") == color and item.get("size") == size:
                    return item.get("sku")
            return ""

        # Precios
        try:
            price_url = f"{proxy_url}/v3/products/price?catalog_reference=ns300"
            price_resp = requests.get(price_url, headers=headers)
            price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []
        except Exception as e:
            _logger.error(f"❌ Error en precios: {e}")
            price_data = []

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
            # --- FIJA EL DEFAULT_CODE/SKU EN LA VARIANTE ---
            sku = get_sku(color_name, size_name)
            if sku:
                variant.default_code = sku
            coste = get_price_cost(color_name, size_name)
            variant.standard_price = coste
            variant.lst_price = coste * 1.25 if coste > 0 else 9.8
            _logger.info(f"💰 Variante: {variant.name} | Coste: {coste}")

        _logger.info(f"✅ Producto NS300 creado correctamente con variantes, SKU y atributos.")

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference=ns300"
        headers.update({"x-toptex-authorization": token})
        inv_resp = requests.get(inventory_url, headers=headers)
        if inv_resp.status_code != 200:
            _logger.error("❌ Error al obtener inventario: " + inv_resp.text)
            return

        inventory_items = inv_resp.json().get("items", [])

        # Busca el template por default_code o por nombre
        template = self.search([
            '|',
            ('default_code', '=', 'NS300'),
            ('name', 'ilike', 'NS300')
        ], limit=1)
        if not template:
            _logger.error("No se encuentra el producto template NS300 (ni por código ni por nombre).")
            return

        StockQuant = self.env['stock.quant']
        for item in inventory_items:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            product = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
            if product:
                quant = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    # Si no hay stock.quant, creamos uno en la ubicación interna principal
                    location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                    if location:
                        StockQuant.create({
                            'product_id': product.id,
                            'location_id': location.id,
                            'quantity': stock,
                            'inventory_quantity': stock,
                        })
                        _logger.info(f"🆕 Stock.quant creado para {sku} con stock {stock}")
                    else:
                        _logger.warning(f"❌ No hay ubicación interna para crear stock.quant de {sku}")
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return

        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers.update({"x-toptex-authorization": token})
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"❌ Error al obtener producto para imágenes: {response.text}")
            return

        data = response.json()[0] if isinstance(response.json(), list) else response.json()
        colors = data.get("colors", [])
        color_images = {
            color.get("colors", {}).get("es", ""): color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
            for color in colors
        }

        template = self.search([
            '|',
            ('default_code', '=', 'NS300'),
            ('name', 'ilike', 'NS300')
        ], limit=1)
        if not template:
            _logger.error("No se encuentra el producto template NS300.")
            return

        for variant in template.product_variant_ids:
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
            color_name = color_val.name if color_val else ""
            img_url = color_images.get(color_name)
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen FACE asignada a {variant.default_code}")