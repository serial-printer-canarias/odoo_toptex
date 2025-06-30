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
    _logger.info(f"🔗 Descargando JSON desde: {url}")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        _logger.error(f"❌ Error descargando JSON desde {url}: {str(e)}")
        raise UserError(f"Error descargando JSON {url}: {str(e)}")

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde: {url}")
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
            img_bin = base64.b64encode(buffer.getvalue())
            _logger.info(f"✅ Imagen convertida y lista para asignar ({len(img_bin)} bytes)")
            return img_bin
        else:
            _logger.warning(f"⚠️ Respuesta no es imagen o fallo al descargar: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error procesando imagen {url}: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_catalog_all(self):
        _logger.info("🚀 INICIO sincronización masiva catálogo TopTex ALL")
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            auth_response.raise_for_status()
            token = auth_response.json().get("token")
        except Exception as e:
            _logger.error(f"❌ Error autenticando en TopTex: {str(e)}")
            raise UserError("❌ No se pudo autenticar en TopTex")

        if not token:
            raise UserError("❌ No se recibió token TopTex")
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}

        # 1. Catálogo (enlace S3)
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        resp = requests.get(catalog_url, headers=headers)
        file_link = resp.json().get("link")
        if not file_link:
            _logger.error("❌ No se recibió el link del catálogo (catalog_url)")
            raise UserError("No se recibió el link del fichero catálogo")
        catalog = get_json_from_link(file_link)
        _logger.info(f"✅ Catálogo descargado: {len(catalog)} productos")

        # 2. Precios ALL (enlace S3)
        price_url = f"{proxy_url}/v3/products/price?result_in_file=1"
        resp_price = requests.get(price_url, headers=headers)
        file_link_price = resp_price.json().get("link")
        prices_json = get_json_from_link(file_link_price)
        sku_price_map = {}
        for item in prices_json.get("items", []):
            sku = item.get("sku")
            price = float(item.get("prices", [{}])[0].get("price", 0.0)) if item.get("prices") else 0.0
            sku_price_map[sku] = price
        _logger.info(f"✅ Precios descargados: {len(sku_price_map)} SKUs")

        for prod in catalog:
            catalog_ref = prod.get("catalogReference", "")
            brand = prod.get("brand", {}).get("name", {}).get("es", "")
            name = prod.get("designation", {}).get("es", "")
            description = prod.get("description", {}).get("es", "")
            images = prod.get("images", [])
            colors = prod.get("colors", [])

            if not catalog_ref or not name:
                _logger.warning(f"❌ Producto sin catalog_ref o sin nombre: {prod}")
                continue

            # Marca
            brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_obj and brand:
                brand_obj = self.env['product.brand'].create({'name': brand})
                _logger.info(f"🆕 Marca creada: {brand}")

            # Atributos
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
                _logger.info("🆕 Atributo Color creado")
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})
                _logger.info("🆕 Atributo Talla creado")

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
                    _logger.info(f"🆕 Color creado: {c}")
                color_vals[c] = val
            for s in all_sizes:
                val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                    _logger.info(f"🆕 Talla creada: {s}")
                size_vals[s] = val

            attribute_lines = [
                {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]}
            ]

            # Plantilla
            template = self.env['product.template'].search([('default_code', '=', catalog_ref)], limit=1)
            if template:
                _logger.warning(f"⚠️ Ya existía plantilla para {catalog_ref}, se actualiza.")
                template.write({
                    'name': f"{brand} {name}",
                    'description_sale': description,
                    'product_brand_id': brand_obj.id if brand_obj else False,
                })
            else:
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
                _logger.info(f"✅ Plantilla creada: {catalog_ref}")

            # Imagen principal
            img_ok = False
            for img in images:
                img_url = img.get("url_image", "")
                if img_url:
                    template.image_1920 = get_image_binary_from_url(img_url)
                    img_ok = True
                    break
            if img_ok:
                _logger.info(f"🖼️ Imagen principal asignada a {catalog_ref}")

            # Coste y precio en variantes
            for variant in template.product_variant_ids:
                sku = variant.default_code
                coste = sku_price_map.get(sku, 0.0)
                variant.standard_price = coste
                variant.lst_price = coste * 1.25 if coste else 9.8
                _logger.info(f"💰 Variante {sku}: coste={coste} pv={variant.lst_price}")

        _logger.info("✅ FIN sincronización catálogo TopTex ALL (productos+variantes+precios coste)")

    # ==== SERVER ACTION STOCK ====
    def sync_toptex_stock_all(self):
        _logger.info("🚀 INICIO actualización masiva de stock TopTex ALL")
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

        inv_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        resp = requests.get(inv_url, headers=headers)
        link = resp.json().get("link")
        inventory = get_json_from_link(link)
        inventory_items = inventory.get("items", []) if isinstance(inventory, dict) else inventory

        StockQuant = self.env['stock.quant']
        ProductProduct = self.env['product.product']
        updated = 0

        for item in inventory_items:
            sku = item.get("sku")
            stock = sum([w.get("stock", 0) for w in item.get("warehouses", [])])
            product = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if product:
                quant = StockQuant.search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal')], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                    if location:
                        StockQuant.create({'product_id': product.id, 'location_id': location.id, 'quantity': stock, 'inventory_quantity': stock})
                        _logger.info(f"🆕 Stock.quant creado para {sku} = {stock}")
                updated += 1
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")

        _logger.info(f"✅ FIN stock TopTex ALL. Variantes actualizadas: {updated}")

    # ==== SERVER ACTION IMÁGENES VARIANTES ====
    def sync_toptex_variant_images_all(self):
        _logger.info("🚀 INICIO asignación imágenes variantes TopTex ALL")
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

        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        resp = requests.get(catalog_url, headers=headers)
        file_link = resp.json().get("link")
        catalog = get_json_from_link(file_link)

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
                            _logger.info(f"🖼️ Imagen variante asignada a {sku} ({color_name})")
        _logger.info(f"✅ FIN asignación imágenes variantes. Variantes actualizadas: {count_img}")