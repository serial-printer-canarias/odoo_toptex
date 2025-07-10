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

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token

        offset = 0
        limit = 50
        while True:
            _logger.info(f"⬇️ Descargando lote {offset} - {offset+limit}")
            product_url = f"{proxy_url}/v3/products/all?offset={offset}&limit={limit}&usage_right=b2b_b2c"
            resp = requests.get(product_url, headers=headers)
            if resp.status_code != 200:
                _logger.warning(f"❌ Error en batch offset={offset}: {resp.text}")
                break

            # Protección robusta ante respuestas mal formateadas
            try:
                batch = resp.json()
            except Exception as e:
                _logger.warning(f"❌ Respuesta malformada al cargar productos: {e}")
                break
            if not batch or not isinstance(batch, list):
                _logger.info("Sin productos o lote vacío, fin de proceso.")
                break

            nuevos = 0
            for data in batch:
                try:
                    catalog_ref = data.get("catalogReference") if isinstance(data, dict) else None
                    if not catalog_ref:
                        _logger.warning("⏭️ Producto sin catalogReference, ignorado.")
                        continue

                    existing = self.env['product.template'].search([('default_code', '=', catalog_ref)], limit=1)
                    if existing:
                        _logger.info(f"⏩ Producto ya existe: {catalog_ref}")
                        continue

                    # BRAND (robusto)
                    brand_data = data.get("brand", {})
                    if isinstance(brand_data, dict):
                        brand_name = brand_data.get("name", {}).get("es", "") or "TopTex"
                    elif isinstance(brand_data, str):
                        brand_name = brand_data
                    else:
                        brand_name = "TopTex"

                    # NAME (robusto)
                    designation_data = data.get("designation", {})
                    if isinstance(designation_data, dict):
                        name = designation_data.get("es", "Producto sin nombre")
                    elif isinstance(designation_data, str):
                        name = designation_data
                    else:
                        name = "Producto sin nombre"

                    # DESCRIPTION (robusto)
                    description_data = data.get("description", {})
                    if isinstance(description_data, dict):
                        description = description_data.get("es", "")
                    elif isinstance(description_data, str):
                        description = description_data
                    else:
                        description = ""

                    full_name = f"{brand_name} {name}".strip()
                    colors = data.get("colors", [])

                    # Extraer todos los colores y tallas
                    all_sizes = set()
                    all_colors = set()
                    for color in colors:
                        c_name = None
                        color_obj = color.get("colors") if isinstance(color, dict) else None
                        if color_obj:
                            if isinstance(color_obj, dict):
                                c_name = color_obj.get("es", "")
                            elif isinstance(color_obj, str):
                                c_name = color_obj
                        if c_name:
                            all_colors.add(c_name)
                        for size in color.get("sizes", []):
                            s_name = size.get("size") if isinstance(size, dict) else size
                            if s_name:
                                all_sizes.add(s_name)

                    # Buscar o crear atributos y valores
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
                        'default_code': catalog_ref,
                        'type': 'consu',
                        'is_storable': True,
                        'description_sale': description,
                        'categ_id': self.env.ref("product.product_category_all").id,
                        'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    }
                    product_template = self.create(template_vals)
                    nuevos += 1
                    _logger.info(f"✅ Producto creado: {catalog_ref} {full_name}")

                    # Imagen principal
                    imgs = data.get("images", [])
                    for img in imgs:
                        img_url = img.get("url_image") if isinstance(img, dict) else ""
                        if img_url:
                            image_bin = get_image_binary_from_url(img_url)
                            if image_bin:
                                product_template.image_1920 = image_bin
                                break

                    # Precios
                    price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                    price_resp = requests.get(price_url, headers=headers)
                    try:
                        price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []
                    except:
                        price_data = []

                    def get_price_cost(color, size):
                        for item in price_data:
                            if item.get("color") == color and item.get("size") == size:
                                prices = item.get("prices", [])
                                if prices:
                                    return float(prices[0].get("price", 0.0))
                        return 0.0

                    # SKUs
                    inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                    inv_resp = requests.get(inv_url, headers=headers)
                    try:
                        inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []
                    except:
                        inventory_items = []

                    def get_sku(color, size):
                        for item in inventory_items:
                            if item.get("color") == color and item.get("size") == size:
                                return item.get("sku")
                        return ""

                    for variant in product_template.product_variant_ids:
                        color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                        size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                        color_name = color_val.name if color_val else ""
                        size_name = size_val.name if size_val else ""
                        sku = get_sku(color_name, size_name)
                        cost = get_price_cost(color_name, size_name)
                        if sku:
                            variant.default_code = sku
                        variant.standard_price = cost
                        variant.lst_price = cost * 1.25 if cost else 9.99
                        _logger.info(f"🧵 Variante creada: {variant.default_code} - {variant.name} - {cost}€")
                except Exception as e:
                    _logger.error(f"❌ Error procesando producto: {str(e)}")
                    continue

            _logger.info(f"🟢 Lote completado: {nuevos} productos nuevos creados.")
            if nuevos == 0:
                _logger.info("Sin productos nuevos en este lote, finalizando.")
                break

            offset += limit

    # --- SERVER ACTION STOCK ---
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        headers["x-toptex-authorization"] = token
        templates = self.search([("default_code", "!=", False)])
        StockQuant = self.env['stock.quant']

        for template in templates:
            try:
                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={template.default_code}"
                inv_resp = requests.get(inv_url, headers=headers)
                inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                for item in inventory_items:
                    sku = item.get("sku")
                    stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
                    variant = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
                    if variant:
                        quant = StockQuant.search([
                            ('product_id', '=', variant.id),
                            ('location_id.usage', '=', 'internal')
                        ], limit=1)
                        if quant:
                            quant.quantity = stock
                            quant.inventory_quantity = stock
                            _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                        else:
                            _logger.warning(f"❌ No se encontró stock.quant para {sku}")
            except Exception as e:
                _logger.error(f"❌ Error actualizando stock de {template.default_code}: {e}")

    # --- SERVER ACTION IMÁGENES POR VARIANTE ---
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return

        headers["x-toptex-authorization"] = token
        templates = self.search([("default_code", "!=", False)])

        for template in templates:
            try:
                url = f"{proxy_url}/v3/products?catalog_reference={template.default_code}&usage_right=b2b_b2c"
                resp = requests.get(url, headers=headers)
                data = resp.json()[0] if isinstance(resp.json(), list) else resp.json()
                color_imgs = {
                    c.get("colors", {}).get("es"): c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                    for c in data.get("colors", [])
                }
                for variant in template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                    color = color_val.name if color_val else ""
                    url_img = color_imgs.get(color)
                    if url_img:
                        image_bin = get_image_binary_from_url(url_img)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🖼️ Imagen asignada a variante {variant.default_code}")
            except Exception as e:
                _logger.error(f"❌ Error asignando imagen a variante: {e}")