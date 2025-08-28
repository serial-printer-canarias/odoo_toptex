# -*- coding: utf-8 -*-
import json
import logging
import requests
import base64
import io
import unicodedata
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------- Helpers ----------
def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=20)
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

def _norm(txt):
    """Normaliza para comparar (sin acentos, minúsculas, trim)."""
    if not txt:
        return ""
    if not isinstance(txt, str):
        txt = str(txt)
    txt = unicodedata.normalize('NFKD', txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.strip().lower()

# ---------- Modelo ----------
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

        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        product_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        resp = requests.get(product_url, headers=headers)
        if resp.status_code != 200:
            _logger.warning(f"❌ Error en página {page_number}: {resp.text}")
            return

        batch = resp.json()
        if isinstance(batch, dict) and "items" in batch:
            batch = batch["items"]
        if not batch:
            _logger.info(f"✅ Sin productos nuevos en esta página, fin de proceso.")
            icp.set_param('toptex_last_page', str(page_number + 1))
            return

        processed_refs = set(self.env['product.template'].search([]).mapped('default_code'))

        skip_keys = {'items', 'page_number', 'total_count', 'page_size'}
        any_valid = False

        for data in batch:
            if not isinstance(data, dict) or any(key in data for key in skip_keys):
                _logger.warning(f"❌ Producto mal formado o ignorado: {data}")
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref:
                _logger.warning(f"❌ Producto sin catalogReference, ignorado: {data}")
                continue
            if catalog_ref in processed_refs:
                _logger.info(f"⏩ Producto ya existe: {catalog_ref}")
                continue

            any_valid = True

            name_data = data.get("designation", {})
            name = name_data.get("es") or name_data.get("en") or "Producto sin nombre"
            name = name.replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()

            description = data.get("description", {}).get("es", "") or data.get("description", {}).get("en", "")
            colors = data.get("colors", [])

            all_sizes = set()
            all_colors = set()
            for color in colors:
                c_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                if not c_name:
                    continue
                all_colors.add(c_name)
                for size in color.get("sizes", []):
                    all_sizes.add(size.get("size"))

            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

            color_vals = {}
            for c in all_colors:
                if not c:
                    continue
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_vals[c] = val

            size_vals = {}
            for s in all_sizes:
                if not s:
                    continue
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
                'type': 'consu',               # Siempre consu
                'is_storable': True,           # Siempre almacenable
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            try:
                product_template = self.create(template_vals)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
                processed_refs.add(catalog_ref)
                _logger.info(f"LOTE OFFSET={page_number} CATALOG_REF={catalog_ref}")
            except Exception as e:
                _logger.error(f"❌ Error creando producto {catalog_ref}: {str(e)}")
                continue

            # Imagen principal de la plantilla (opcional)
            try:
                for img in data.get("images", []):
                    img_url = img.get("url_image")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product_template.image_1920 = image_bin
                            break
            except Exception as e:
                _logger.warning(f"⚠️ No se pudo asignar imagen a {catalog_ref}: {str(e)}")

            # Precios/SKUs por variante
            try:
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers)
                price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                def get_price_cost(color, size):
                    for item in price_data:
                        if item.get("color") == color and item.get("size") == size:
                            prices = item.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers)
                inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                def get_sku(color, size):
                    for item in inventory_items:
                        if item.get("color") == color and item.get("size") == size:
                            return item.get("sku")
                    return ""

                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == 'Color')
                    size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == 'Talla')
                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""
                    sku = get_sku(color_name, size_name)
                    cost = get_price_cost(color_name, size_name)
                    if sku:
                        variant.default_code = sku
                    variant.standard_price = cost
                    variant.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante creada: {variant.default_code} - {variant.name} - {cost}€")
            except Exception as e:
                _logger.warning(f"⚠️ Error en precios/SKUs de {catalog_ref}: {str(e)}")

        if not any_valid:
            _logger.info(f"✅ Lote página={page_number}, sin productos nuevos.")
        icp.set_param('toptex_last_page', str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # --- Stock (solo consu almacenable, en WH/Stock) ---
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
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']

        warehouse = self.env['stock.warehouse'].search([], limit=1)
        location = warehouse.lot_stock_id if warehouse else self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

        products = ProductProduct.search([("default_code", "!=", False)])
        for variant in products:
            if variant.type != 'consu' or not variant.product_tmpl_id.is_storable:
                _logger.info(f"⏭️ Skip {variant.default_code} (type={variant.type}, is_storable={variant.product_tmpl_id.is_storable})")
                continue

            sku = variant.default_code
            inv_url = f"{proxy_url}/v3/products/{sku}/inventory"
            inv_resp = requests.get(inv_url, headers=headers)
            if inv_resp.status_code != 200:
                _logger.warning(f"❌ Error inventario SKU {sku}: {inv_resp.text}")
                continue

            try:
                data_json = inv_resp.json()
                warehouses = []
                if isinstance(data_json, dict):
                    warehouses = data_json.get("warehouses", [])
                elif isinstance(data_json, list) and data_json and isinstance(data_json[0], dict):
                    warehouses = data_json[0].get("warehouses", [])
                stock = 0
                for wh in warehouses:
                    if isinstance(wh, dict) and wh.get("id") == "toptex":
                        stock = wh.get("stock", 0)
                        break
                _logger.info(f"SKU {sku} Warehouses: {warehouses} | Stock usado: {stock}")
            except Exception as e:
                _logger.error(f"❌ JSON error SKU {sku}: {e}")
                stock = 0

            quant = StockQuant.search([
                ('product_id', '=', variant.id),
                ('location_id', '=', location.id)
            ], limit=1)

            if quant:
                quant.quantity = stock
                quant.inventory_quantity = stock
                quant.write({'quantity': stock, 'inventory_quantity': stock})
                _logger.info(f"✅ stock.quant creado y actualizado para {sku} en WH/Stock: {stock}")
            else:
                if location:
                    StockQuant.create({
                        'product_id': variant.id,
                        'location_id': location.id,
                        'quantity': stock,
                        'inventory_quantity': stock,
                    })
                    _logger.info(f"✅ stock.quant creado y actualizado para {sku} en WH/Stock: {stock}")
                else:
                    _logger.warning(f"❌ No se encontró ubicación interna para crear quant para {sku}")

    # --- Imágenes por variante (robusto: primero por SKU, luego por Color) ---
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

        def best_packshot(color_node):
            ps = color_node.get("packshots") or {}
            for key in ("FACE", "PACKSHOT", "FRONT", "MAIN"):
                url_try = (ps.get(key) or {}).get("url_packshot")
                if url_try:
                    return url_try
            for img in (color_node.get("images") or []):
                role = _norm(img.get("role") or img.get("type"))
                if role in ("face", "packshot", "front", "main"):
                    u = img.get("url_image") or img.get("url")
                    if u:
                        return u
            imgs = color_node.get("images") or []
            if imgs:
                return imgs[0].get("url_image") or imgs[0].get("url")
            return None

        for template in templates:
            catalog_ref = template.default_code

            # 1) Datos del producto para obtener color -> url
            prod_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
            prod_resp = requests.get(prod_url, headers=headers, timeout=20)
            try:
                data_json = prod_resp.json()
            except Exception:
                _logger.warning(f"❌ Respuesta no JSON para {catalog_ref}, saltando.")
                continue

            items = []
            if isinstance(data_json, dict) and data_json.get("items"):
                items = data_json["items"]
            elif isinstance(data_json, list):
                items = data_json
            elif isinstance(data_json, dict) and data_json:
                items = [data_json]

            if not items:
                _logger.warning(f"❌ Sin datos para {catalog_ref}, saltando.")
                continue

            data = items[0]

            # mapa color_norm -> url
            color_to_url = {}
            for c in data.get("colors", []) or []:
                names = []
                cdict = c.get("colors") or {}
                if isinstance(cdict, dict):
                    names += [cdict.get("es"), cdict.get("en"), cdict.get("fr"), cdict.get("name")]
                for k in ("color", "code", "colorCode"):
                    if c.get(k):
                        names.append(c.get(k))
                url_img = best_packshot(c)
                if not url_img:
                    continue
                for n in filter(None, names):
                    color_to_url[_norm(n)] = url_img

            # 2) Inventario por catalog_ref para cruzar SKU -> color_norm
            sku_to_color = {}
            inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
            inv_resp = requests.get(inv_url, headers=headers, timeout=20)
            if inv_resp.status_code == 200:
                inv_items = inv_resp.json().get("items", []) if isinstance(inv_resp.json(), dict) else inv_resp.json()
                for it in inv_items or []:
                    sku = it.get("sku")
                    color_name = it.get("color")
                    if sku and color_name:
                        sku_to_color[sku] = _norm(color_name)

            if not color_to_url and not sku_to_color:
                _logger.warning(f"⚠️ {catalog_ref}: sin mapa de colores ni SKUs para imágenes.")
                continue

            # 3) Asignación por variante
            for variant in template.product_variant_ids:
                # Prioridad 1: por SKU
                img_url = None
                sku = variant.default_code
                color_norm = sku_to_color.get(sku)
                if color_norm and color_to_url.get(color_norm):
                    img_url = color_to_url[color_norm]
                else:
                    # Prioridad 2: por nombre de Color
                    color_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: _norm(v.attribute_id.name) == 'color'
                    )
                    v_color = _norm(color_val.name if color_val else "")
                    if v_color:
                        img_url = color_to_url.get(v_color)
                        if not img_url:
                            # match "contains" por si hay diferencias mínimas
                            for k, u in color_to_url.items():
                                if v_color in k or k in v_color:
                                    img_url = u
                                    break

                if not img_url:
                    _logger.info(f"🔎 {catalog_ref}/{variant.default_code}: sin imagen (no match SKU/Color).")
                    continue

                try:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🖼️ Imagen asignada a variante {variant.default_code}")
                except Exception as e:
                    _logger.warning(f"⚠️ Falló asignación de imagen a {variant.default_code}: {e}")