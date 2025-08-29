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
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=20)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = (auth_response.json().get("token") or "").strip()
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token

        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        product_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        resp = requests.get(product_url, headers=headers, timeout=30)
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
                {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]},
            ]

            template_vals = {
                'name': full_name,
                'default_code': catalog_ref,
                'type': 'consu',               # siempre consu
                'is_storable': True,           # almacenable para permitir quants
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

            try:
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers, timeout=20)
                price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                def get_price_cost(color, size):
                    for item in price_data:
                        if item.get("color") == color and item.get("size") == size:
                            prices = item.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers, timeout=20)
                inventory_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

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
                    variant.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante creada: {variant.default_code} - {variant.name} - {cost}€")
            except Exception as e:
                _logger.warning(f"⚠️ Error en precios/SKUs de {catalog_ref}: {str(e)}")

        if not any_valid:
            _logger.info(f"✅ Lote página={page_number}, sin productos nuevos.")
        icp.set_param('toptex_last_page', str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # --- Server Action: Stock (solo consu almacenable) ---
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        headers["x-toptex-authorization"] = (token or "").strip()
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']

        products = ProductProduct.search([("default_code", "!=", False)])
        for variant in products:
            if variant.type != 'consu' or not variant.product_tmpl_id.is_storable:
                _logger.info(f"⏭️ Skip {variant.default_code} (type={variant.type}, is_storable={variant.product_tmpl_id.is_storable})")
                continue

            sku = variant.default_code
            inv_url = f"{proxy_url}/v3/products/{sku}/inventory"
            inv_resp = requests.get(inv_url, headers=headers, timeout=20)
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
                ('location_id.usage', '=', 'internal')
            ], limit=1)

            if quant:
                quant.quantity = stock
                quant.inventory_quantity = stock
                quant.write({'quantity': stock, 'inventory_quantity': stock})
                _logger.info(f"✅ stock.quant creado y actualizado para {sku}: {stock}")
            else:
                location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                if location:
                    StockQuant.create({
                        'product_id': variant.id,
                        'location_id': location.id,
                        'quantity': stock,
                        'inventory_quantity': stock,
                    })
                    _logger.info(f"✅ stock.quant creado y actualizado para {sku}: {stock}")
                else:
                    _logger.warning(f"❌ No se encontró ubicación interna para crear quant para {sku}")

    # --- Server Action: Imágenes por variante (ARREGLADA: por SKU) ---
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = (token or "").strip()

        # Vamos variante por variante (usamos su SKU real)
        variants = self.env['product.product'].search([("default_code", "!=", False)])
        for variant in variants:
            sku = variant.default_code
            try:
                # Llamada correcta: ?sku=...&usage_right=b2b_b2c
                url = f"{proxy_url}/v3/products?sku={requests.utils.quote(sku)}&usage_right=b2b_b2c"
                resp = requests.get(url, headers=headers, timeout=25)
                if resp.status_code != 200:
                    _logger.warning(f"❌ [{sku}] HTTP {resp.status_code} al obtener producto: {resp.text}")
                    continue

                try:
                    payload = resp.json()
                except Exception:
                    _logger.warning(f"❌ [{sku}] Respuesta no es JSON. Saltando.")
                    continue

                data = payload[0] if isinstance(payload, list) and payload else (payload if isinstance(payload, dict) else {})
                if not data:
                    _logger.warning(f"❌ [{sku}] Sin datos de producto. Saltando.")
                    continue

                # 1) Intento por SKU dentro de cada color/talla
                chosen_url = ""
                chosen_color = ""
                for c in data.get("colors", []):
                    sizes = c.get("sizes", []) or []
                    # preferimos FACE, si no FRONT/MODEL
                    pack = c.get("packshots", {}) or {}
                    face = (pack.get("FACE") or {})
                    front = (pack.get("FRONT") or {})
                    model = (pack.get("MODEL") or {})
                    url_pack = face.get("url_packshot") or front.get("url_packshot") or model.get("url_packshot") or ""
                    for s in sizes:
                        if s.get("sku") == sku:
                            chosen_url = url_pack
                            chosen_color = (c.get("colors", {}).get("es")
                                            or c.get("colors", {}).get("en")
                                            or "")
                            break
                    if chosen_url:
                        break

                # 2) Fallback por nombre del atributo "Color" si no hubo match por SKU
                if not chosen_url:
                    color_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.name.lower() == 'color'
                    )
                    color_name_attr = color_val.name if color_val else ""
                    if color_name_attr:
                        for c in data.get("colors", []):
                            c_name = (c.get("colors", {}).get("es")
                                      or c.get("colors", {}).get("en")
                                      or "")
                            if c_name and c_name.lower() == color_name_attr.lower():
                                pack = c.get("packshots", {}) or {}
                                face = (pack.get("FACE") or {})
                                front = (pack.get("FRONT") or {})
                                model = (pack.get("MODEL") or {})
                                chosen_url = face.get("url_packshot") or front.get("url_packshot") or model.get("url_packshot") or ""
                                chosen_color = c_name
                                break

                if not chosen_url:
                    _logger.warning(f"❌ [{sku}] Sin packshot para el color/talla. Saltando.")
                    continue

                image_bin = get_image_binary_from_url(chosen_url)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen asignada a variante {sku} (color={chosen_color})")
                else:
                    _logger.warning(f"⚠️ [{sku}] No se pudo descargar la imagen: {chosen_url}")

            except Exception as e:
                _logger.warning(f"⚠️ [{sku}] Error inesperado asignando imagen: {e}")