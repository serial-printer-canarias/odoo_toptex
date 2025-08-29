# -*- coding: utf-8 -*-
import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Utilidad: descargar imagen y convertir a JPG base64 (maneja RGBA -> RGB)
# ---------------------------------------------------------------------------
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -----------------------------------------------------------------------
    # Carga de catálogo (igual que tenías)
    # -----------------------------------------------------------------------
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
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=30)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = (auth_response.json() or {}).get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        product_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        resp = requests.get(product_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.warning(f"❌ Error en página {page_number}: {resp.text}")
            return

        batch = resp.json()
        if isinstance(batch, dict) and "items" in batch:
            batch = batch["items"]
        if not batch:
            _logger.info("✅ Sin productos nuevos en esta página, fin de proceso.")
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

            all_sizes, all_colors = set(), set()
            for color in colors:
                c_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                if c_name:
                    all_colors.add(c_name)
                for size in color.get("sizes", []):
                    if size.get("size"):
                        all_sizes.add(size.get("size"))

            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or \
                         self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or \
                        self.env['product.attribute'].create({'name': 'Talla'})

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

            template_vals = {
                'name': full_name,
                'default_code': catalog_ref,
                'type': 'consu',          # SIEMPRE CONSU (como acordamos)
                'is_storable': True,      # almacenable para gestionar quants
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            try:
                product_template = self.create(template_vals)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
                processed_refs.add(catalog_ref)
            except Exception as e:
                _logger.error(f"❌ Error creando producto {catalog_ref}: {str(e)}")
                continue

            # Imagen principal de template (opcional, primera del array)
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

            # Precios + SKUs por color/talla
            try:
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers, timeout=30)
                price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                def get_price_cost(color, size):
                    for item in price_data:
                        if item.get("color") == color and item.get("size") == size:
                            prices = item.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers, timeout=30)
                inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                def get_sku(color, size):
                    for item in inventory_items:
                        if item.get("color") == color and item.get("size") == size:
                            return item.get("sku")
                    return ""

                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == size_attr.id)
                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""
                    sku = get_sku(color_name, size_name)
                    cost = get_price_cost(color_name, size_name)
                    if sku:
                        variant.default_code = sku
                    variant.standard_price = cost
                    variant.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante: {variant.default_code} - {variant.name} - {cost}€")
            except Exception as e:
                _logger.warning(f"⚠️ Error en precios/SKUs de {catalog_ref}: {str(e)}")

        if not any_valid:
            _logger.info(f"✅ Lote página={page_number}, sin productos nuevos.")
        icp.set_param('toptex_last_page', str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # -----------------------------------------------------------------------
    # Stock (el bloque que ya estaba probado en tu entorno)
    # -----------------------------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(
            auth_url,
            json={"username": username, "password": password},
            headers=headers,
            timeout=20
        ).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers["x-toptex-authorization"] = str(token).strip()

        Product = self.env['product.product']
        Quant = self.env['stock.quant']
        Location = self.env['stock.location']

        internal_loc = Location.search([('usage', '=', 'internal')], limit=1)
        if not internal_loc:
            _logger.warning("❌ No hay ubicación interna para crear quants.")
            return

        for variant in Product.search([('default_code', '!=', False)]):
            # Solo consu y almacenable (tu requisito)
            if variant.type != 'consu' or not variant.product_tmpl_id.is_storable:
                continue

            sku = variant.default_code
            inv_url = f"{proxy}/v3/products/{sku}/inventory"
            r = requests.get(inv_url, headers=headers, timeout=20)
            if r.status_code != 200:
                _logger.warning(f"❌ Inventario {sku}: {r.status_code} {r.text}")
                continue

            try:
                js = r.json()
                warehouses = js.get("warehouses", []) if isinstance(js, dict) else (
                    js[0].get("warehouses", []) if isinstance(js, list) and js else [])
                stock = 0
                for wh in warehouses:
                    if isinstance(wh, dict) and wh.get("id") == "toptex":
                        stock = int(wh.get("stock", 0))
                        break
            except Exception as e:
                _logger.error(f"❌ JSON inventario {sku}: {e}")
                stock = 0

            quant = Quant.search([('product_id', '=', variant.id),
                                  ('location_id', '=', internal_loc.id)], limit=1)
            if quant:
                quant.write({'quantity': stock, 'inventory_quantity': stock})
            else:
                Quant.create({
                    'product_id': variant.id,
                    'location_id': internal_loc.id,
                    'quantity': stock,
                    'inventory_quantity': stock
                })
            _logger.info(f"✅ stock.quant actualizado para {sku}: {stock}")

    # -----------------------------------------------------------------------
    # Imágenes por variante (nuevo: endpoint por SKU con packshots)
    # -----------------------------------------------------------------------
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(
            auth_url,
            json={"username": username, "password": password},
            headers=headers,
            timeout=20
        ).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = str(token).strip()

        Product = self.env['product.product']

        def _pick_packshot_url(packshots):
            """Prioriza FACE, luego cualquier otro packshot disponible."""
            if not isinstance(packshots, dict):
                return None
            for k in ["FACE", "FRONT", "MAIN", "PACKSHOT", "BACK", "SIDE", "DETAIL_1", "DETAIL_2"]:
                u = (packshots.get(k) or {}).get("url_packshot")
                if u:
                    return u
            return None

        for variant in Product.search([('default_code', '!=', False)]):
            sku = variant.default_code
            url = f"{proxy}/v3/products?sku={sku}&usage_right=b2b_b2c"
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code != 200:
                _logger.warning(f"❌ Sin datos para SKU {sku}: {r.status_code} {r.text}. Saltando.")
                continue

            try:
                data = r.json() or {}
            except Exception as e:
                _logger.warning(f"❌ JSON inválido para SKU {sku}: {e}")
                continue

            # Normalizar distintas formas de respuesta
            item = None
            if isinstance(data, dict) and data.get("items"):
                # formato: {"items":[{...}]}
                item = data["items"][0] if data["items"] else None
            elif isinstance(data, list) and data:
                item = data[0]
            elif isinstance(data, dict):
                item = data

            if not isinstance(item, dict):
                _logger.warning(f"❌ Respuesta sin contenido útil para {sku}.")
                continue

            url_img = None

            # 1) packshots a nivel raíz del item (algunas respuestas lo traen así)
            url_img = _pick_packshot_url(item.get("packshots", {}))

            # 2) si no, buscar en colores del item
            if not url_img:
                for c in item.get("colors", []) or []:
                    url_img = _pick_packshot_url(c.get("packshots", {}))
                    if url_img:
                        break

            # 3) fallback: array de images
            if not url_img:
                for im in item.get("images", []) or []:
                    u = im.get("url_image")
                    if u:
                        url_img = u
                        break

            if url_img:
                image_bin = get_image_binary_from_url(url_img)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen asignada a variante {sku}")
                else:
                    _logger.warning(f"⚠️ No se pudo descargar imagen para {sku}")
            else:
                _logger.warning(f"❌ [SKU {sku}] Sin packshot/imagen en API. Saltando.")