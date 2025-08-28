# -*- coding: utf-8 -*-
import json
import logging
import requests
import base64
import io
import re
import unicodedata
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ----------------------- Utilidades -----------------------

def _normalize_text(s):
    """Normaliza nombres de color para hacer matching robusto."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s.strip().lower())
    return s

def _to_hex_color(v):
    """
    Intenta convertir varios formatos (dict, lista, '255,0,0', 'FF0000', '#FF0000')
    a una cadena '#RRGGBB'. Devuelve '' si no se puede.
    """
    if v is None:
        return ""
    try:
        # dict {'r':255,'g':0,'b':0} o {'R':...}
        if isinstance(v, dict):
            r = int(v.get('r') or v.get('R'))
            g = int(v.get('g') or v.get('G'))
            b = int(v.get('b') or v.get('B'))
            return "#{:02X}{:02X}{:02X}".format(r, g, b)
        # lista/tupla [255,0,0]
        if isinstance(v, (list, tuple)) and len(v) == 3:
            r, g, b = [int(x) for x in v]
            return "#{:02X}{:02X}{:02X}".format(r, g, b)
        # cadena
        if isinstance(v, str):
            s = v.strip()
            # '255,0,0'
            if re.match(r"^\s*\d+\s*,\s*\d+\s*,\s*\d+\s*$", s):
                r, g, b = [int(x) for x in s.split(",")]
                return "#{:02X}{:02X}{:02X}".format(r, g, b)
            # '#FF0000' o 'FF0000'
            s = s.upper()
            if s.startswith("#"):
                s = s[1:]
            if re.match(r"^[0-9A-F]{6}$", s):
                return f"#{s}"
    except Exception:
        pass
    return ""

def get_image_binary_from_url(url):
    """Descarga una imagen y devuelve base64 JPG seguro (sin alfa)."""
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=15)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(response.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90)
            return base64.b64encode(buffer.getvalue())
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {str(e)}")
    return None

# ----------------------- Modelo -----------------------

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

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers).json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token

        # Paginación
        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        # Batch de productos por catálogo
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
            name = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()
            description = data.get("description", {}).get("es", "") or data.get("description", {}).get("en", "")
            colors_api = data.get("colors", []) or []

            # Atributos Color/Talla
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or \
                         self.env['product.attribute'].create({'name': 'Color'})
            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or \
                        self.env['product.attribute'].create({'name': 'Talla'})

            # Map color -> hex (si viene en el JSON) y crear valores
            color_vals_map = {}
            size_vals_map = {}

            # Preparamos set de todos los colores y tallas y sus posibles HEX
            color_hex_by_name = {}
            all_sizes = set()
            all_colors = set()
            for c in colors_api:
                cname = c.get("colors", {}).get("es") or c.get("colors", {}).get("en") or ""
                if cname:
                    all_colors.add(cname)
                    # Buscar posibles campos de color en el JSON
                    hex_guess = _to_hex_color(
                        c.get("rgb") or c.get("rgb_code") or c.get("hex") or c.get("hexColor") or c.get("colorHex")
                    )
                    if not hex_guess:
                        # Algunos catálogos usan 'color_code' estilo 'FFCC00'
                        hex_guess = _to_hex_color(c.get("color_code"))
                    if hex_guess:
                        color_hex_by_name[_normalize_text(cname)] = hex_guess

                for s in (c.get("sizes") or []):
                    sz = s.get("size")
                    if sz:
                        all_sizes.add(sz)

            # Crear/obtener valores Color con html_color si lo tenemos
            for cname in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', cname),
                                                                  ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': cname, 'attribute_id': color_attr.id})
                # Actualizar html_color si nos viene el HEX
                hex_for_c = color_hex_by_name.get(_normalize_text(cname), "")
                if hex_for_c and getattr(val, "html_color", None) != hex_for_c:
                    try:
                        val.write({'html_color': hex_for_c})
                    except Exception:
                        pass
                color_vals_map[cname] = val

            # Crear/obtener valores Talla
            for sz in all_sizes:
                val = self.env['product.attribute.value'].search([('name', '=', sz),
                                                                  ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': sz, 'attribute_id': size_attr.id})
                size_vals_map[sz] = val

            attribute_lines = [
                {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals_map.values()])]},
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals_map.values()])]},
            ]

            template_vals = {
                'name': full_name,
                'default_code': catalog_ref,
                'type': 'consu',              # siempre consumo
                'is_storable': True,          # flag propio
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

            # Imagen principal del template (si hubiera)
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

            # Precios / SKUs por variante
            try:
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers)
                price_items = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers)
                inv_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                def get_cost(cname, sname):
                    for it in price_items:
                        if it.get("color") == cname and it.get("size") == sname:
                            prices = it.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                def get_sku(cname, sname):
                    for it in inv_items:
                        if it.get("color") == cname and it.get("size") == sname:
                            return it.get("sku")
                    return ""

                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == size_attr.id)
                    cname = color_val.name if color_val else ""
                    sname = size_val.name if size_val else ""

                    sku = get_sku(cname, sname)
                    cost = get_cost(cname, sname)

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

    # -------------------- Stock (sin cambios funcionales) --------------------

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

        products = ProductProduct.search([("default_code", "!=", False)])
        for variant in products:
            # Solo consu y almacenable
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
                ('location_id.usage', '=', 'internal')
            ], limit=1)

            if quant:
                quant.write({'quantity': stock, 'inventory_quantity': stock})
                _logger.info(f"✅ stock.quant actualizado para {sku}: {stock}")
            else:
                location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                if location:
                    StockQuant.create({
                        'product_id': variant.id,
                        'location_id': location.id,
                        'quantity': stock,
                        'inventory_quantity': stock,
                    })
                    _logger.info(f"✅ stock.quant creado para {sku}: {stock}")
                else:
                    _logger.warning(f"❌ No se encontró ubicación interna para crear quant para {sku}")

    # ---------------- Imágenes por variante (mejorado) ----------------

    def sync_variant_images_from_api(self):
        """
        Asigna imagen a cada variante:
        1) Mapeo por Color: usa packshot de color (FACE/SIDE/BACK).
        2) Fallback por SKU: si no se encuentra por color, intenta consultar por sku.
        Además, si en la respuesta viene RGB/HEX del color, actualiza html_color.
        """
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
        ColorAttr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)

        for template in templates:
            # 1) Consulta por catalog_reference
            url = f"{proxy_url}/v3/products?catalog_reference={template.default_code}&usage_right=b2b_b2c"
            resp = requests.get(url, headers=headers)

            try:
                data_json = resp.json()
            except Exception:
                _logger.warning(f"❌ Sin datos válidos para {template.default_code}, saltando.")
                continue

            if isinstance(data_json, list) and data_json:
                data = data_json[0]
            elif isinstance(data_json, dict) and data_json:
                data = data_json
            else:
                _logger.warning(f"❌ Sin datos para {template.default_code}, saltando.")
                continue

            # Construir mapa color -> url packshot y (si está) color HEX
            color_img = {}
            color_hex = {}
            for c in data.get("colors", []) or []:
                c_name = c.get("colors", {}).get("es") or c.get("colors", {}).get("en") or ""
                norm = _normalize_text(c_name)
                # Preferencia FACE; si no, cualquier packshot disponible
                packshots = (c.get("packshots") or {})
                url_face = (packshots.get("FACE") or {}).get("url_packshot") or ""
                if not url_face:
                    # buscar cualquier clave que tenga url_packshot
                    for v in packshots.values():
                        url_face = v.get("url_packshot") or ""
                        if url_face:
                            break
                if url_face and norm:
                    color_img[norm] = url_face

                # Guardar HEX si viene
                hex_guess = _to_hex_color(
                    c.get("rgb") or c.get("rgb_code") or c.get("hex") or c.get("hexColor") or c.get("colorHex") or c.get("color_code")
                )
                if hex_guess and norm:
                    color_hex[norm] = hex_guess

            # Actualizar html_color de los valores de Color del template
            if ColorAttr:
                for pav in template.attribute_line_ids.filtered(lambda l: l.attribute_id.id == ColorAttr.id).value_ids:
                    norm = _normalize_text(pav.name)
                    hx = color_hex.get(norm, "")
                    if hx and getattr(pav, "html_color", None) != hx:
                        try:
                            pav.write({'html_color': hx})
                        except Exception:
                            pass

            # Asignar imagen por variante: primero por Color, luego fallback por SKU
            for variant in template.product_variant_ids:
                # Color de la variante
                color_val = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id and v.attribute_id.name and v.attribute_id.name.lower() == 'color'
                )
                variant_color = color_val.name if color_val else ""
                norm_color = _normalize_text(variant_color)

                used = False
                # Intento por Color
                if norm_color and norm_color in color_img:
                    bin_img = get_image_binary_from_url(color_img[norm_color])
                    if bin_img:
                        variant.image_1920 = bin_img
                        _logger.info(f"🖼️ Imagen por COLOR asignada a {variant.default_code} ({variant_color})")
                        used = True

                # Fallback por SKU
                if not used and variant.default_code:
                    try:
                        sku_url = f"{proxy_url}/v3/products?sku={variant.default_code}"
                        r2 = requests.get(sku_url, headers=headers)
                        if r2.status_code == 200:
                            dj = r2.json()
                            dj = dj[0] if isinstance(dj, list) and dj else dj
                            # 1) Buscar packshot directo
                            url_img = ""
                            if isinstance(dj, dict):
                                # packshots a nivel de color dentro del SKU
                                packshots = (dj.get("packshots") or {})
                                url_img = (packshots.get("FACE") or {}).get("url_packshot") or ""
                                if not url_img:
                                    for v in packshots.values():
                                        url_img = v.get("url_packshot") or ""
                                        if url_img:
                                            break
                                # fallback: primera imagen genérica
                                if not url_img:
                                    for im in (dj.get("images") or []):
                                        url_img = im.get("url_image") or ""
                                        if url_img:
                                            break
                            if url_img:
                                bin_img = get_image_binary_from_url(url_img)
                                if bin_img:
                                    variant.image_1920 = bin_img
                                    _logger.info(f"🖼️ Imagen por SKU asignada a {variant.default_code}")
                                    used = True
                    except Exception as e:
                        _logger.warning(f"⚠️ Fallback SKU falló para {variant.default_code}: {e}")

                if not used:
                    _logger.warning(f"❌ Sin imagen para variante {variant.default_code} ({variant_color})")