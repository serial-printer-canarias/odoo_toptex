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
        response = requests.get(url, stream=True, timeout=15)
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
    def sync_product_catalog_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # --- Autenticación
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

        # --- Descarga catálogo (enlace a JSON)
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        resp = requests.get(catalog_url, headers=headers)
        if resp.status_code != 200:
            raise UserError(f"❌ Error al obtener el catálogo: {resp.status_code} - {resp.text}")
        link = resp.json().get("link")
        if not link:
            raise UserError("❌ No se recibió link del catálogo.")
        _logger.info(f"🗂️ Link JSON catálogo recibido: {link}")

        file_resp = requests.get(link, timeout=120)
        if file_resp.status_code != 200:
            raise UserError("❌ Error al descargar el archivo del catálogo.")
        try:
            catalog = file_resp.json()
        except Exception as e:
            _logger.error(f"❌ Error leyendo JSON catálogo: {e}")
            raise UserError(f"Error al parsear JSON catálogo: {e}")
        _logger.info(f"🗂️ Catálogo cargado. Productos: {len(catalog)}")

        brand_obj = self.env['product.brand']
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        created_count = 0
        for prod in catalog:
            try:
                # --- Marca robusta
                brand_name = (prod.get("brand", {}).get("name", {}).get("es", "") or prod.get("brand", {}).get("name", {}).get("en", "")).strip()
                brand_name = brand_name if brand_name else "Sin Marca"
                brand_id = False
                existing_brand = brand_obj.search([('name', 'ilike', brand_name)], limit=1)
                if not existing_brand:
                    brand_id = brand_obj.create({'name': brand_name}).id
                    _logger.info(f"🚀 Marca creada: {brand_name}")
                else:
                    brand_id = existing_brand.id

                name = prod.get("designation", {}).get("es", "Producto sin nombre")
                description = prod.get("description", {}).get("es", "")
                default_code = prod.get("catalogReference", "")

                categ_id = self.env.ref("product.product_category_all").id

                # --- Variantes
                colors = prod.get("colors", [])
                all_colors = set()
                all_sizes = set()
                for color in colors:
                    color_name = color.get("colors", {}).get("es", "")
                    all_colors.add(color_name)
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

                attribute_lines = []
                if color_vals:
                    attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]})
                if size_vals:
                    attribute_lines.append({'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]})

                # --- CREA/ACTUALIZA plantilla
                template = self.search([('default_code', '=', default_code)], limit=1)
                vals = {
                    'name': f"{brand_name} {name}".strip(),
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': categ_id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    'brand_id': brand_id,
                }
                if not template:
                    template = self.create(vals)
                    created_count += 1
                    _logger.info(f"🆕 Producto creado: {template.name}")
                else:
                    template.write(vals)
                    _logger.info(f"✏️ Producto actualizado: {template.name}")

                # --- Imagen principal (opcional)
                images = prod.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            template.image_1920 = image_bin
                            break
            except Exception as e:
                _logger.error(f"❌ ERROR en producto: {prod.get('catalogReference', 'sin referencia')} | {e}")
                continue

        _logger.info(f"✅ Importación finalizada. Nuevos productos: {created_count}")

    # ----- SERVER ACTION: Imagenes por variante -----
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # --- Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes de variantes.")
            return

        # --- Llama al endpoint all para imágenes por variantes
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        resp = requests.get(catalog_url, headers=headers)
        if resp.status_code != 200:
            _logger.error(f"❌ Error al obtener catálogo para imágenes: {resp.text}")
            return
        link = resp.json().get("link")
        if not link:
            _logger.error("❌ No se recibió link para imágenes variantes.")
            return
        file_resp = requests.get(link, timeout=120)
        catalog = file_resp.json() if file_resp.status_code == 200 else []
        ProductProduct = self.env['product.product']

        count_img = 0
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
                            count_img += 1
                            _logger.info(f"🖼️ Imagen FACE asignada a {sku}")
        _logger.info(f"✅ FIN asignación imágenes por variantes. Total: {count_img}")

    # ----- SERVER ACTION: Stock -----
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # --- Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        # --- Llama a inventory all (link json)
        stock_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        resp = requests.get(stock_url, headers=headers)
        if resp.status_code != 200:
            _logger.error(f"❌ Error al obtener inventario all: {resp.text}")
            return
        link = resp.json().get("link")
        if not link:
            _logger.error("❌ No se recibió link de inventario.")
            return
        file_resp = requests.get(link, timeout=120)
        stock_data = file_resp.json().get("items", []) if file_resp.status_code == 200 else []
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']

        count_stock = 0
        for item in stock_data:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            product = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if product:
                quants = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ])
                if quants:
                    for quant in quants:
                        quant.quantity = stock
                        quant.inventory_quantity = stock
                    count_stock += 1
                    _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    _logger.warning(f"❌ No se encontró stock.quant para {sku}")
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")
        _logger.info(f"✅ FIN actualización stock. Total variantes actualizadas: {count_stock}")