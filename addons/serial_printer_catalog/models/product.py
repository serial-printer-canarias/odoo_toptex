import json
import logging
import requests
import time
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
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {str(e)}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_toptex(self):
        # --- PARTE 1: Autenticación y Descarga del JSON ---
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Obtener enlace temporal de productos
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Esperar hasta que el JSON esté disponible
        max_wait = 7 * 60  # 7 minutos en segundos
        wait_interval = 20
        waited = 0
        products_data = None

        while waited < max_wait:
            _logger.info(f"⏳ Esperando JSON... ({waited}s/{max_wait}s)")
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, dict) and 'items' in products_data:
                    break
            except Exception:
                pass
            time.sleep(wait_interval)
            waited += wait_interval

        if not products_data or 'items' not in products_data:
            raise UserError("❌ El JSON de productos no estuvo disponible después de esperar.")

        product_list = products_data.get("items", [])
        if not product_list:
            raise UserError("❌ El catálogo descargado no es una lista de productos válida.")

        _logger.info(f"🟢 Procesando {len(product_list)} productos TopTex...")

        # --- PARTE 2: Crear Productos Plantilla y Variantes (sin imagen ni stock) ---

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        for prod in product_list:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            # Recoge todos los colores/tallas de variantes
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                all_colors.add(color_name)
                for size in color.get("sizes", []):
                    all_sizes.add(size.get("size", ""))

            # Crea los valores de atributos si no existen
            color_vals = {}
            for c in all_colors:
                if not c: continue
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals[c] = val
            size_vals = {}
            for s in all_sizes:
                if not s: continue
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                size_vals[s] = val

            # Construir attribute_lines solo si hay valores
            attribute_lines = []
            if color_vals:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                })
            if size_vals:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                })

            # ¿Ya existe producto plantilla?
            tmpl = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                template_vals = {
                    'name': f"{brand} {name}".strip(),
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                }
                tmpl = self.create(template_vals)

        _logger.info("✅ Productos plantilla y variantes creados. Ahora imágenes y stock...")

        # --- PARTE 3: Añadir imágenes y stock a variantes ya creadas ---

        for prod in product_list:
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            tmpl = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                continue
            colors = prod.get("colors", [])
            images = prod.get("images", [])
            # Imagen principal plantilla (la primera imagen general)
            if images:
                img_url = images[0].get("url_image")
                if img_url:
                    img_bin = get_image_binary_from_url(img_url)
                    if img_bin:
                        tmpl.image_1920 = img_bin
            # Buscar variantes y asignar imágenes y stock/price
            for variant in tmpl.product_variant_ids:
                # Atributos de la variante
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""
                for color in colors:
                    col_name = color.get("colors", {}).get("es", "")
                    if col_name == color_name:
                        for sz in color.get("sizes", []):
                            if sz.get("size") == size_name:
                                # SKU
                                variant.default_code = sz.get("sku", "")
                                # Precio coste/venta
                                prices = sz.get("prices", [])
                                if prices:
                                    variant.standard_price = float(prices[0].get("price", 0.0))
                                    variant.lst_price = float(prices[0].get("price", 0.0)) * 1.25
                                # Imagen variante (FACE de color)
                                img_url = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                                if img_url:
                                    img_bin = get_image_binary_from_url(img_url)
                                    if img_bin:
                                        variant.image_1920 = img_bin
                                # Stock (puedes personalizar a tu lógica)
                                stock = sz.get("stock", 0)
                                quant = self.env['stock.quant'].search([
                                    ('product_id', '=', variant.id),
                                    ('location_id.usage', '=', 'internal')
                                ], limit=1)
                                if quant:
                                    quant.quantity = stock
                                    quant.inventory_quantity = stock

        _logger.info("✅ Sincronización completa de productos TopTex.")