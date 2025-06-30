import json
import logging
import requests
import base64
import io
import zipfile
import gzip
from PIL import Image
from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen: {url}")
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(response.content))
            # Fondo blanco si tiene transparencia
            if image.mode in ('RGBA', 'LA'):
                bg = Image.new("RGB", image.size, (255,255,255))
                bg.paste(image, mask=image.split()[-1])
                image = bg
            else:
                image = image.convert("RGB")
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue())
    except Exception as e:
        _logger.warning(f"❌ Error procesando imagen {url}: {e}")
    return None

def get_json_from_link(url):
    _logger.info(f"🔗 Descargando catálogo desde: {url}")
    try:
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        # ZIP
        if "zip" in ct or url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for fname in z.namelist():
                    if fname.endswith(".json"):
                        with z.open(fname) as f:
                            data = json.load(f)
                            _logger.info(f"✅ JSON extraído de ZIP: {fname} ({len(data)} items)")
                            return data
        # GZIP
        elif "gzip" in ct or url.endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as f:
                data = json.load(f)
                _logger.info(f"✅ JSON extraído de GZ ({len(data)} items)")
                return data
        # JSON plano
        else:
            data = r.json()
            _logger.info(f"✅ JSON recibido ({len(data)} items)")
            return data
    except Exception as e:
        _logger.error(f"❌ Error descargando/descomprimiendo {url}: {e}")
        raise UserError(f"Error al descargar JSON: {e}")

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_catalog_all(self):
        """Programado en scheduled action, crea/actualiza todo el catálogo."""
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales/parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        if resp.status_code != 200:
            raise UserError(f"❌ Error autenticando: {resp.status_code} - {resp.text}")
        token = resp.json().get("token")
        if not token:
            raise UserError("❌ No se recibió token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # Descarga el link de catálogo completo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers_catalog = {"x-api-key": api_key, "x-toptex-authorization": token}
        resp = requests.get(catalog_url, headers=headers_catalog)
        if resp.status_code != 200:
            raise UserError(f"❌ Error obteniendo link catálogo: {resp.status_code} - {resp.text}")
        file_link = resp.json().get("link")
        if not file_link:
            raise UserError("❌ No se encontró link al catálogo en la respuesta.")
        _logger.info(f"📥 Link recibido: {file_link}")

        # Descarga y descomprime catálogo
        catalog = get_json_from_link(file_link)
        # Por si es un diccionario con key 'items'
        if isinstance(catalog, dict) and "items" in catalog:
            catalog = catalog["items"]

        # Pre-Indexa atributos existentes
        attr_obj = self.env['product.attribute']
        color_attr = attr_obj.search([('name', '=', 'Color')], limit=1) or attr_obj.create({'name': 'Color'})
        size_attr = attr_obj.search([('name', '=', 'Talla')], limit=1) or attr_obj.create({'name': 'Talla'})
        brand_obj = self.env['product.brand'] if 'product.brand' in self.env else False

        total, creados, actualizados = 0, 0, 0
        for prod in catalog:
            total += 1
            # Marca
            brand = prod.get("brand", {}).get("name", {}).get("es", "") or prod.get("brand", {}).get("name", {}).get("en", "") or ""
            brand = brand or "Sin Marca"
            brand_id = False
            if brand_obj:
                brand_id = brand_obj.search([('name', '=', brand)], limit=1)
                if not brand_id:
                    brand_id = brand_obj.create({'name': brand})
                brand_id = brand_id.id

            # Nombre y descripción
            designation = prod.get("designation", {}).get("es", prod.get("designation", {}).get("en", "Producto sin nombre"))
            description = prod.get("description", {}).get("es", prod.get("description", {}).get("en", ""))
            catalog_ref = prod.get("catalogReference", "")
            # Para Product Template el default_code será el catalog_ref, como en NS300
            default_code = catalog_ref

            # --- VARIANTES: recolecta todos los valores posibles ---
            all_colors, all_sizes = set(), set()
            for color in prod.get("colors", []):
                cname = color.get("colors", {}).get("es", color.get("colors", {}).get("en", ""))
                if cname: all_colors.add(cname)
                for sz in color.get("sizes", []):
                    sname = sz.get("size", "")
                    if sname: all_sizes.add(sname)
            # Atributos y valores
            color_vals, size_vals = {}, {}
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
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                }
            ]

            # Busca si ya existe producto por catalog_ref (default_code)
            template = self.search([('default_code', '=', default_code)], limit=1)
            template_vals = {
                'name': f"{brand} {designation}".strip(),
                'default_code': default_code,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                'type': 'consu',
                'is_storable': True,
            }
            if brand_id:
                template_vals['brand_id'] = brand_id

            if not template:
                template = self.create(template_vals)
                creados += 1
                _logger.info(f"✅ Producto creado: {default_code}")
            else:
                template.write(template_vals)
                actualizados += 1
                _logger.info(f"🔄 Producto actualizado: {default_code}")

            # Imagen principal
            images = prod.get("images", [])
            for img in images:
                img_url = img.get("url_image", "")
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        template.image_1920 = image_bin
                        break

            # Variantes: asigna SKU y precios
            for color in prod.get("colors", []):
                cname = color.get("colors", {}).get("es", color.get("colors", {}).get("en", ""))
                for sz in color.get("sizes", []):
                    sname = sz.get("size", "")
                    sku = sz.get("sku", "")
                    price = None
                    if sz.get("prices", []):
                        price = float(sz["prices"][0].get("price", 0))
                    # Encuentra variante por atributos
                    variant = template.product_variant_ids.filtered(
                        lambda v: any(val.name == cname and val.attribute_id.id == color_attr.id for val in v.product_template_attribute_value_ids) and
                                  any(val.name == sname and val.attribute_id.id == size_attr.id for val in v.product_template_attribute_value_ids)
                    )
                    if variant:
                        if sku:
                            variant.default_code = sku
                        if price:
                            variant.standard_price = price
                            variant.lst_price = price * 1.25 if price > 0 else 9.8

        _logger.info(f"✅ Catálogo terminado. Procesados: {total} | Creados: {creados} | Actualizados: {actualizados}")

    # ------------------- Server Action para Stock -------------------
    @api.model
    def sync_stock_catalog_all(self):
        """Llama a /v3/products/inventory/result_in_file=1 y actualiza stock por SKU"""
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        # Autenticación
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        # Link de inventario
        inventory_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        inv_resp = requests.get(inventory_url, headers=headers)
        file_link = inv_resp.json().get("link")
        inventory = get_json_from_link(file_link)
        # Por si viene como dict/items
        if isinstance(inventory, dict) and "items" in inventory:
            inventory = inventory["items"]

        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']
        count = 0
        for item in inventory:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            product = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if product:
                quant = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                else:
                    StockQuant.create({
                        'product_id': product.id,
                        'location_id': product._default_stock_location().id,
                        'quantity': stock,
                        'inventory_quantity': stock,
                    })
                count += 1
                _logger.info(f"📦 Stock actualizado: {sku}={stock}")
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")
        _logger.info(f"FIN actualización stock: {count} variantes")

    # ------------------- Server Action para imágenes por variante -------------------
    @api.model
    def sync_variant_images_catalog_all(self):
        """Asigna imágenes FACE por variante a cada producto del catálogo."""
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        # Autenticación
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes variantes.")
            return

        # Catálogo completo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        resp = requests.get(catalog_url, headers=headers)
        file_link = resp.json().get("link")
        catalog = get_json_from_link(file_link)
        if isinstance(catalog, dict) and "items" in catalog:
            catalog = catalog["items"]

        ProductProduct = self.env['product.product']
        count_img = 0
        for prod in catalog:
            colors = prod.get("colors", [])
            for color in colors:
                color_name = color.get("colors", {}).get("es", color.get("colors", {}).get("en", ""))
                img_url = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for sz in color.get("sizes", []):
                    sku = sz.get("sku", "")
                    product = ProductProduct.search([('default_code', '=', sku)], limit=1)
                    if product and img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product.image_1920 = image_bin
                            count_img += 1
                            _logger.info(f"🖼️ Imagen FACE asignada a {sku}")
        _logger.info(f"✅ FIN asignación imágenes variantes: {count_img}")