# -*- coding: utf-8 -*-
import io
import re
import json
import time
import base64
import logging
import requests
from PIL import Image
from difflib import get_close_matches

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# -------------------------------
# Utilidades de imágenes/colores
# -------------------------------
def _normalize_color_name(name: str) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"\(.*?\)", "", s)        # quita paréntesis
    s = s.split("/")[0]                  # quita textos tras '/'
    repl = {"ó":"o","á":"a","é":"e","í":"i","ú":"u","-":" ","_":" "}
    for k, v in repl.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    aliases = {
        "graphite grey": "graphite gray",
        "light grey": "light gray",
        "grey": "gray",
    }
    return aliases.get(s, s)


def _rgb_to_hex(r, g, b):
    try:
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        return "#{:02X}{:02X}{:02X}".format(r, g, b)
    except Exception:
        return None


def _extract_hex_from_color_node(c):
    """Intenta sacar un #RRGGBB de un nodo de color de TopTex."""
    if not isinstance(c, dict):
        return None
    rgb = c.get("rgb") or c.get("RGB") or c.get("color_rgb")
    if isinstance(rgb, dict):
        return _rgb_to_hex(rgb.get("r"), rgb.get("g"), rgb.get("b"))
    if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
        return _rgb_to_hex(rgb[0], rgb[1], rgb[2])
    for key in ("rgb", "RGB", "color_rgb", "hex", "hex_code", "colorHex"):
        val = c.get(key)
        if isinstance(val, str):
            v = val.strip()
            if v.startswith("#") and len(v) in (4, 7):
                if len(v) == 4:
                    return "#{}{}{}{}{}{}".format(v[1]*2, v[2]*2, v[3]*2)
                return v.upper()
            m = re.match(r"^\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*$", v)
            if m:
                return _rgb_to_hex(m.group(1), m.group(2), m.group(3))
    return None


def _choose_packshot_url(packshots):
    """Escoge la mejor URL de packshot disponible con orden de preferencia y fallback."""
    if not isinstance(packshots, dict):
        return None
    up = {str(k).upper(): v for k, v in packshots.items() if isinstance(k, str)}
    order = ["FACE", "FRONT", "3Q", "SIDE", "LEFT", "RIGHT", "BACK", "PACKSHOT", "FLAT", "DEFAULT", "MAIN"]
    for key in order:
        node = up.get(key)
        if isinstance(node, dict) and node.get("url_packshot"):
            return node.get("url_packshot")
    # último recurso: cualquiera que tenga url_packshot
    for node in up.values():
        if isinstance(node, dict) and node.get("url_packshot"):
            return node.get("url_packshot")
    return None


def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        r = requests.get(url, stream=True, timeout=15)
        ctype = r.headers.get("Content-Type", "")
        if r.status_code == 200 and "image" in ctype:
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return base64.b64encode(buf.getvalue())
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {e}")
    return None


# -------------------------------------------------
# Product Template (creación + stock + imágenes)
# -------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -----------------------
    # Carga de productos
    # -----------------------
    @api.model
    def sync_product_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")
        api_key  = icp.get_param("toptex_api_key")
        proxy    = icp.get_param("toptex_proxy_url")

        if not all([username, password, api_key, proxy]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise UserError(f"❌ Error autenticando: {resp.status_code} - {resp.text}")
        token = resp.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param("toptex_last_page") or 1)
        page_size = 50

        url = f"{proxy}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code != 200:
            _logger.warning(f"❌ Error en página {page_number}: {r.text}")
            return

        batch = r.json()
        if isinstance(batch, dict) and "items" in batch:
            batch = batch["items"] or []
        if not batch:
            _logger.info("✅ Sin productos nuevos en esta página.")
            icp.set_param("toptex_last_page", str(page_number + 1))
            return

        processed_refs = set(self.env["product.template"].search([]).mapped("default_code"))
        any_valid = False
        skip_keys = {"items", "page_number", "total_count", "page_size"}

        Attr = self.env["product.attribute"]
        AttrVal = self.env["product.attribute.value"]

        for data in batch:
            if not isinstance(data, dict) or any(k in data for k in skip_keys):
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref:
                _logger.warning("❌ Producto sin catalogReference, ignorado.")
                continue
            if catalog_ref in processed_refs:
                _logger.info(f"⏩ Ya existe: {catalog_ref}")
                continue

            any_valid = True
            name_data = data.get("designation", {}) or {}
            name = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()
            description = (data.get("description", {}) or {}).get("es") or (data.get("description", {}) or {}).get("en") or ""

            colors = data.get("colors", []) or []
            all_sizes, all_colors = set(), set()
            color_hex_map = {}
            for c in colors:
                c_name = (c.get("colors", {}) or {}).get("es") or (c.get("colors", {}) or {}).get("en") or ""
                if c_name:
                    all_colors.add(c_name)
                    hexcode = _extract_hex_from_color_node(c)
                    if hexcode:
                        color_hex_map[c_name] = hexcode
                for s in c.get("sizes", []) or []:
                    all_sizes.add(s.get("size"))

            color_attr = Attr.search([("name", "=", "Color")], limit=1)
            if not color_attr:
                color_attr = Attr.create({"name": "Color", "display_type": "color"})
            else:
                try:
                    color_attr.display_type = "color"
                except Exception:
                    pass

            size_attr  = Attr.search([("name", "=", "Talla")], limit=1) or Attr.create({"name": "Talla"})

            color_vals = {}
            for c_name in all_colors:
                if not c_name:
                    continue
                val = AttrVal.search([("name", "=", c_name), ("attribute_id", "=", color_attr.id)], limit=1)
                if not val:
                    val = AttrVal.create({"name": c_name, "attribute_id": color_attr.id})
                hexcode = color_hex_map.get(c_name)
                if hexcode and getattr(val, "html_color", False) is not None:
                    if not val.html_color:
                        val.html_color = hexcode
                color_vals[c_name] = val

            size_vals = {}
            for s_name in all_sizes:
                if not s_name:
                    continue
                val = AttrVal.search([("name", "=", s_name), ("attribute_id", "=", size_attr.id)], limit=1) \
                      or AttrVal.create({"name": s_name, "attribute_id": size_attr.id})
                size_vals[s_name] = val

            attribute_lines = [
                {"attribute_id": color_attr.id, "value_ids": [(6, 0, [v.id for v in color_vals.values()])]},
                {"attribute_id": size_attr.id,  "value_ids": [(6, 0, [v.id for v in size_vals.values()])]},
            ]

            vals = {
                "name": full_name,
                "default_code": catalog_ref,
                "type": "consu",
                "is_storable": True,
                "description_sale": description,
                "categ_id": self.env.ref("product.product_category_all").id,
                "attribute_line_ids": [(0, 0, l) for l in attribute_lines],
            }
            try:
                tmpl = self.create(vals)
                processed_refs.add(catalog_ref)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
            except Exception as e:
                _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                continue

            try:
                price_url = f"{proxy}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers, timeout=30)
                price_items = price_resp.json().get("items", []) if price_resp.status_code == 200 else []

                inv_url = f"{proxy}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers, timeout=30)
                inv_items = inv_resp.json().get("items", []) if inv_resp.status_code == 200 else []

                def get_cost(color, size):
                    for row in price_items:
                        if row.get("color") == color and row.get("size") == size:
                            prices = row.get("prices", []) or []
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                def get_sku(color, size):
                    for row in inv_items:
                        if row.get("color") == color and row.get("size") == size:
                            return row.get("sku") or ""
                    return ""

                for v in tmpl.product_variant_ids:
                    cval = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.id == color_attr.id)
                    sval = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.id == size_attr.id)
                    c_name = cval.name if cval else ""
                    s_name = sval.name if sval else ""
                    sku = get_sku(c_name, s_name)
                    cost = get_cost(c_name, s_name)
                    if sku:
                        v.default_code = sku
                    v.standard_price = cost
                    v.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante {v.default_code} - {v.name} coste={cost}")
            except Exception as e:
                _logger.warning(f"⚠️ Precios/SKUs {catalog_ref}: {e}")

        if not any_valid:
            _logger.info(f"✅ Lote página={page_number}, sin productos nuevos.")
        icp.set_param("toptex_last_page", str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # -------------------------------------------------
    # Stock (WH/Stock) + OFFSET reanudable
    # -------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        proxy    = icp.get_param("toptex_proxy_url")
        api_key  = icp.get_param("toptex_api_key")
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")

        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Product = self.env["product.product"]
        Quant   = self.env["stock.quant"]
        wh = self.env["stock.warehouse"].search([], limit=1)
        location = wh.lot_stock_id if wh else self.env["stock.location"].search([("usage", "=", "internal")], limit=1)
        if not location:
            _logger.warning("❌ No hay ubicación interna para crear quants.")
            return

        last_id = int(icp.get_param("toptex_stock_last_id") or 0)
        variants = Product.search([("id", ">", last_id), ("default_code", "!=", False)], order="id", limit=2000)
        if not variants:
            variants = Product.search([("default_code", "!=", False)], order="id", limit=2000)
            last_id = 0

        start = time.monotonic()
        new_last = last_id
        processed = False

        for v in variants:
            new_last = v.id
            processed = True

            if v.type != "consu" or not v.product_tmpl_id.is_storable:
                continue

            sku = v.default_code
            inv_url = f"{proxy}/v3/products/{sku}/inventory"
            r = requests.get(inv_url, headers=headers, timeout=20)
            if r.status_code != 200:
                _logger.warning(f"❌ Inventario {sku}: {r.status_code} {r.text}")
                continue

            try:
                js = r.json()
                whs = js.get("warehouses", []) if isinstance(js, dict) else (js[0].get("warehouses", []) if isinstance(js, list) and js else [])
                stock = 0
                for whrow in whs:
                    if isinstance(whrow, dict) and whrow.get("id") == "toptex":
                        stock = int(whrow.get("stock", 0))
                        break
            except Exception as e:
                _logger.error(f"❌ JSON inventario {sku}: {e}")
                stock = 0

            quant = Quant.search([("product_id", "=", v.id), ("location_id", "=", location.id)], limit=1)
            if quant:
                quant.write({"quantity": stock, "inventory_quantity": stock})
            else:
                Quant.create({"product_id": v.id, "location_id": location.id, "quantity": stock, "inventory_quantity": stock})
            _logger.info(f"✅ stock.quant creado/actualizado para {sku} en WH/Stock: {stock}")

            if time.monotonic() - start > 85:
                icp.set_param("toptex_stock_last_id", str(new_last))
                _logger.warning(f"⏱️ Tiempo límite alcanzado (stock). Guardando offset en {new_last} y saliendo.")
                return

        if processed:
            icp.set_param("toptex_stock_last_id", str(new_last))
            _logger.info(f"STOCK offset guardado: {new_last}")
        else:
            icp.set_param("toptex_stock_last_id", "0")
            _logger.info("STOCK offset reiniciado a 0.")

    # -------------------------------------------------------------------
    # Imágenes por variante (robusto + reanudable + matching por color)
    # -------------------------------------------------------------------
    def sync_variant_images_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        proxy    = icp.get_param("toptex_proxy_url")
        api_key  = icp.get_param("toptex_api_key")
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")

        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers, timeout=30).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = token.strip()

        last_id = int(icp.get_param("toptex_img_last_id") or 0)
        Variant = self.env["product.product"]

        variants = Variant.search([("id", ">", last_id), ("default_code", "!=", False)], order="id", limit=600)
        if not variants:
            variants = Variant.search([("default_code", "!=", False)], order="id", limit=600)
            last_id = 0

        start = time.monotonic()
        processed_any = False
        new_last_id = last_id

        def _extract_color_map(product_json):
            """Devuelve dict {color_normalizado: url_packshot} con fallback de vistas."""
            cmap = {}
            if not isinstance(product_json, dict):
                return cmap
            for c in product_json.get("colors", []) or []:
                col = (c.get("colors", {}) or {}).get("es") or (c.get("colors", {}) or {}).get("en") or ""
                packshots = (c.get("packshots", {}) or {})
                url = _choose_packshot_url(packshots)
                if not url:
                    # ultra-fallback: si hay 'images' a nivel de color
                    imgs = c.get("images") or []
                    if isinstance(imgs, list) and imgs:
                        # busca la primera imagen con url_image
                        for im in imgs:
                            if isinstance(im, dict) and im.get("url_image"):
                                url = im["url_image"]
                                break
                if col and url:
                    cmap[_normalize_color_name(col)] = url
            return cmap

        def _fetch_by_sku(sku):
            try:
                url = f"{proxy}/v3/products?sku={sku}&usage_right=b2b_b2c"
                r = requests.get(url, headers=headers, timeout=25)
                if r.status_code != 200:
                    return None
                data = r.json()
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                _logger.warning(f"❌ Error SKU fetch ({sku}): {e}")
            return None

        def _fetch_by_catalog_ref(catalog_ref):
            try:
                url = f"{proxy}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
                r = requests.get(url, headers=headers, timeout=25)
                if r.status_code != 200:
                    return None
                data = r.json()
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                _logger.warning(f"❌ Error catalog_ref fetch ({catalog_ref}): {e}")
            return None

        for v in variants:
            new_last_id = v.id
            processed_any = True

            color_pav = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.name.lower() == "color")
            color_name = color_pav.name if color_pav else ""
            norm_color = _normalize_color_name(color_name)

            sku = v.default_code or ""
            catalog_ref = v.product_tmpl_id.default_code or ""

            # 1) Intento por SKU
            pack_url = None
            data = _fetch_by_sku(sku)
            cmap = _extract_color_map(data or {})
            if cmap:
                pack_url = cmap.get(norm_color)
                if not pack_url:
                    close = get_close_matches(norm_color, list(cmap.keys()), n=1, cutoff=0.85)
                    if close:
                        pack_url = cmap.get(close[0])

            # 2) Fallback por catalog_reference
            if not pack_url and catalog_ref:
                cdata = _fetch_by_catalog_ref(catalog_ref)
                cmap2 = _extract_color_map(cdata or {})
                if cmap2:
                    pack_url = cmap2.get(norm_color)
                    if not pack_url:
                        close = get_close_matches(norm_color, list(cmap2.keys()), n=1, cutoff=0.85)
                        if close:
                            pack_url = cmap2.get(close[0])

            if not pack_url:
                _logger.warning(f"❌ Sin packshot para SKU/color: {sku} ({color_name}). Saltando.")
            else:
                img_bin = get_image_binary_from_url(pack_url)
                if img_bin:
                    try:
                        v.write({"image_1920": img_bin})
                        _logger.info(f"✅ Imagen asignada a variante {sku} ({color_name})")
                    except Exception as e:
                        _logger.warning(f"⚠️ No se pudo guardar imagen de {sku}: {e}")

            if time.monotonic() - start > 85:
                icp.set_param("toptex_img_last_id", str(new_last_id))
                _logger.warning(f"⏱️ Tiempo límite alcanzado, guardando offset y saliendo. IMG offset guardado: {new_last_id}")
                return

        if processed_any:
            icp.set_param("toptex_img_last_id", str(new_last_id))
            _logger.info(f"IMG offset guardado: {new_last_id}")
        else:
            icp.set_param("toptex_img_last_id", "0")
            _logger.info("IMG offset reiniciado a 0 (no había más variantes).")