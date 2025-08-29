# -*- coding: utf-8 -*-
import io
import json
import base64
import logging
import requests
import re
from PIL import Image

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# -------------------------------
# Utils
# -------------------------------
def get_image_binary_from_url(url):
    """Descarga una imagen y la devuelve en base64 (JPEG, sin transparencia)."""
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(r.content))
            if image.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", image.size, (255, 255, 255))
                bg.paste(image, mask=image.split()[-1])
                image = bg
            else:
                image = image.convert("RGB")
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue())
        _logger.warning(f"⚠️ Respuesta no imagen: {url} -> {r.status_code}")
    except Exception as e:
        _logger.warning(f"❌ Error imagen {url}: {e}")
    return None


def _norm(s):
    """Normaliza para comparar colores (sin espacios, lowercase)."""
    return re.sub(r"\s+", "", (s or "")).strip().lower()


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -------------------------------------------------
    # 1) Importación de productos (lotes, variantes, SKUs, precios)
    # -------------------------------------------------
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
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers, timeout=30)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param("toptex_last_page") or 1)
        page_size   = 50

        url = f"{proxy}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.warning(f"❌ Error página {page_number}: {resp.text}")
            return

        batch = resp.json()
        if isinstance(batch, dict) and "items" in batch:
            batch = batch["items"]

        if not batch:
            _logger.info("✅ Sin productos nuevos en esta página.")
            icp.set_param("toptex_last_page", str(page_number + 1))
            return

        processed_refs = set(self.env["product.template"].search([]).mapped("default_code"))
        skip_keys = {"items", "page_number", "total_count", "page_size"}
        any_valid = False

        # Atributos Color / Talla
        attr_color = self.env["product.attribute"].search([("name", "=", "Color")], limit=1) \
                     or self.env["product.attribute"].create({"name": "Color"})
        attr_size  = self.env["product.attribute"].search([("name", "=", "Talla")], limit=1) \
                     or self.env["product.attribute"].create({"name": "Talla"})

        for data in batch:
            if not isinstance(data, dict) or any(k in data for k in skip_keys):
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref or catalog_ref in processed_refs:
                continue

            any_valid = True

            name_data = data.get("designation", {}) or {}
            name = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()

            description = (data.get("description", {}) or {}).get("es", "") or (data.get("description", {}) or {}).get("en", "")
            colors = data.get("colors", []) or []

            all_colors = set()
            all_sizes  = set()
            for c in colors:
                cname = (c.get("colors", {}) or {}).get("es") or (c.get("colors", {}) or {}).get("en")
                if not cname:
                    continue
                all_colors.add(cname)
                for s in c.get("sizes", []) or []:
                    all_sizes.add(s.get("size"))

            # valores atributos
            color_vals = {}
            for c in all_colors:
                val = self.env["product.attribute.value"].search([("name", "=", c), ("attribute_id", "=", attr_color.id)], limit=1) \
                      or self.env["product.attribute.value"].create({"name": c, "attribute_id": attr_color.id})
                color_vals[c] = val

            size_vals = {}
            for s in all_sizes:
                val = self.env["product.attribute.value"].search([("name", "=", s), ("attribute_id", "=", attr_size.id)], limit=1) \
                      or self.env["product.attribute.value"].create({"name": s, "attribute_id": attr_size.id})
                size_vals[s] = val

            attribute_lines = [
                {"attribute_id": attr_color.id, "value_ids": [(6, 0, [v.id for v in color_vals.values()])]},
                {"attribute_id": attr_size.id,  "value_ids": [(6, 0, [v.id for v in size_vals.values()])]},
            ]

            vals = {
                "name": full_name,
                "default_code": catalog_ref,
                "type": "consu",           # seguimos 'consu'
                "is_storable": True,       # almacenable para stock
                "description_sale": description,
                "categ_id": self.env.ref("product.product_category_all").id,
                "attribute_line_ids": [(0, 0, l) for l in attribute_lines],
            }
            try:
                template = self.create(vals)
                processed_refs.add(catalog_ref)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
            except Exception as e:
                _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                continue

            # Imagen del template
            try:
                for img in data.get("images", []) or []:
                    u = img.get("url_image")
                    if u:
                        b = get_image_binary_from_url(u)
                        if b:
                            template.image_1920 = b
                            break
            except Exception as e:
                _logger.warning(f"⚠️ Imagen template {catalog_ref}: {e}")

            # Precios + SKUs por variante
            try:
                price_url = f"{proxy}/v3/products/price?catalog_reference={catalog_ref}"
                price_resp = requests.get(price_url, headers=headers, timeout=30)
                price_items = (price_resp.json().get("items", []) if price_resp.status_code == 200 else [])

                def get_cost(cn, sn):
                    for it in price_items:
                        if it.get("color") == cn and it.get("size") == sn:
                            pr = (it.get("prices") or [])
                            if pr:
                                return float(pr[0].get("price", 0.0))
                    return 0.0

                inv_url = f"{proxy}/v3/products/inventory?catalog_reference={catalog_ref}"
                inv_resp = requests.get(inv_url, headers=headers, timeout=30)
                inv_items = (inv_resp.json().get("items", []) if inv_resp.status_code == 200 else [])

                def get_sku(cn, sn):
                    for it in inv_items:
                        if it.get("color") == cn and it.get("size") == sn:
                            return it.get("sku") or ""
                    return ""

                for variant in template.product_variant_ids:
                    col_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == attr_color.id)
                    siz_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == attr_size.id)
                    col = col_val.name if col_val else ""
                    siz = siz_val.name if siz_val else ""

                    sku  = get_sku(col, siz)
                    cost = get_cost(col, siz)
                    if sku:
                        variant.default_code = sku
                    variant.standard_price = cost
                    variant.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante: {variant.default_code} | {variant.name} | {cost}€")
            except Exception as e:
                _logger.warning(f"⚠️ Precios/SKUs {catalog_ref}: {e}")

        if not any_valid:
            _logger.info(f"✅ Lote página={page_number}, sin productos nuevos.")
        icp.set_param("toptex_last_page", str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # -------------------------------------------------
    # 2) Stock (solo consu almacenable, siempre WH/Stock)  ***VERSIÓN PRO***
    # -------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password},
                              headers=headers).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        headers["x-toptex-authorization"] = token
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']

        # Usar la ubicación interna PRINCIPAL del almacén principal
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

    # -------------------------------------------------
    # 3) Imágenes por variante (por SKU, con fallback por color)
    # -------------------------------------------------
    def sync_variant_images_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        proxy   = icp.get_param("toptex_proxy_url")
        api_key = icp.get_param("toptex_api_key")
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Product = self.env["product.product"].sudo()

        for variant in Product.search([("default_code", "!=", False)]):
            sku = variant.default_code

            # 1) Petición por SKU
            url = f"{proxy}/v3/products?sku={sku}&usage_right=b2b_b2c"
            r = requests.get(url, headers=headers, timeout=30)
            data = None
            if r.status_code == 200:
                try:
                    j = r.json()
                    if isinstance(j, dict) and j.get("items"):
                        data = j["items"][0]
                    elif isinstance(j, list) and j:
                        data = j[0]
                    elif isinstance(j, dict):
                        data = j
                except Exception:
                    data = None

            img_url = None

            # 2) Imagen directa si viene en "images"
            if data:
                imgs = (data.get("images") or [])
                if imgs:
                    img_url = (imgs[0] or {}).get("url_image") or None

                # 3) Fallback: packshot por color (FACE) o primera imagen del color
                if not img_url:
                    color_imgs = {}
                    for c in (data.get("colors") or []):
                        name_es = ((c.get("colors") or {}).get("es")) or ""
                        name_en = ((c.get("colors") or {}).get("en")) or ""
                        face = (((c.get("packshots") or {}).get("FACE") or {}).get("url_packshot")) or ""
                        if not face:
                            imgs_c = (c.get("images") or [])
                            if imgs_c:
                                face = (imgs_c[0] or {}).get("url_image") or ""

                        if face:
                            color_imgs[_norm(name_es)] = face
                            color_imgs[_norm(name_en)] = face

                    col_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color")
                    col_name = _norm(col_val.name if col_val else "")
                    img_url = color_imgs.get(col_name)

            if img_url:
                b = get_image_binary_from_url(img_url)
                if b:
                    variant.image_1920 = b
                    _logger.info(f"🖼️ Imagen asignada a variante {variant.default_code}")
                    continue

            _logger.warning(f"❌ Sin packshot para el SKU/color: {variant.default_code}. Saltando.")