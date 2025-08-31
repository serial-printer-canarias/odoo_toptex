# -*- coding: utf-8 -*-
import io
import time
import json
import base64
import logging
import requests
from PIL import Image

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# -------------------------------------------------
# Utils
# -------------------------------------------------
def get_image_binary_from_url(url):
    """Descarga una imagen y la devuelve en base64 (JPEG RGB)."""
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        r = requests.get(url, stream=True, timeout=20)
        ct = r.headers.get("Content-Type", "")
        if r.status_code == 200 and "image" in ct:
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            return base64.b64encode(buf.getvalue())
        _logger.warning(f"⚠️ Contenido no imagen o status != 200: {ct} {r.status_code}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen: {e}")
    return None


# -------------------------------------------------
# Modelo
# -------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -------------------------------------------------
    # Carga de productos (como ya lo tenías)
    # -------------------------------------------------
    @api.model
    def sync_product_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")
        api_key = icp.get_param("toptex_api_key")
        proxy_url = icp.get_param("toptex_proxy_url")

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(
            auth_url, json={"username": username, "password": password}, headers=headers, timeout=30
        ).json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token

        page_number = int(icp.get_param("toptex_last_page") or 1)
        page_size = 50

        # Lote
        product_url = (
            f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        )
        resp = requests.get(product_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.warning(f"❌ Error página {page_number}: {resp.status_code} {resp.text}")
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

        for data in batch:
            if not isinstance(data, dict) or any(k in data for k in skip_keys):
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref:
                _logger.warning(f"❌ Producto sin catalogReference, ignorado: {data}")
                continue
            if catalog_ref in processed_refs:
                _logger.info(f"⏩ Ya existe: {catalog_ref}")
                continue

            any_valid = True

            name_data = data.get("designation", {}) or {}
            name = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()

            description = data.get("description", {}).get("es", "") or data.get("description", {}).get("en", "")
            colors = data.get("colors", []) or []

            all_sizes, all_colors = set(), set()
            for c in colors:
                cname = (c.get("colors") or {}).get("es") or (c.get("colors") or {}).get("en") or ""
                if cname:
                    all_colors.add(cname)
                for s in c.get("sizes", []) or []:
                    all_sizes.add(s.get("size"))

            # Atributos
            attr_obj = self.env["product.attribute"]
            attr_val = self.env["product.attribute.value"]
            color_attr = attr_obj.search([("name", "=", "Color")], limit=1) or attr_obj.create({"name": "Color"})
            size_attr = attr_obj.search([("name", "=", "Talla")], limit=1) or attr_obj.create({"name": "Talla"})

            color_vals, size_vals = {}, {}
            for c in all_colors:
                if not c:
                    continue
                v = attr_val.search([("name", "=", c), ("attribute_id", "=", color_attr.id)], limit=1) or \
                    attr_val.create({"name": c, "attribute_id": color_attr.id})
                color_vals[c] = v
            for s in all_sizes:
                if not s:
                    continue
                v = attr_val.search([("name", "=", s), ("attribute_id", "=", size_attr.id)], limit=1) or \
                    attr_val.create({"name": s, "attribute_id": size_attr.id})
                size_vals[s] = v

            attribute_lines = [
                {"attribute_id": color_attr.id, "value_ids": [(6, 0, [v.id for v in color_vals.values()])]},
                {"attribute_id": size_attr.id, "value_ids": [(6, 0, [v.id for v in size_vals.values()])]},
            ]

            template_vals = {
                "name": full_name,
                "default_code": catalog_ref,
                "type": "consu",            # consu por definición
                "is_storable": True,        # almacenable
                "description_sale": description,
                "categ_id": self.env.ref("product.product_category_all").id,
                "attribute_line_ids": [(0, 0, line) for line in attribute_lines],
            }

            try:
                template = self.create(template_vals)
                processed_refs.add(catalog_ref)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
            except Exception as e:
                _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                continue

            # Imagen de plantilla (primera válida)
            try:
                for img in data.get("images", []) or []:
                    u = img.get("url_image")
                    if u:
                        b64 = get_image_binary_from_url(u)
                        if b64:
                            template.image_1920 = b64
                            break
            except Exception as e:
                _logger.warning(f"⚠️ Imagen plantilla {catalog_ref}: {e}")

            # Precios + SKU por variante
            try:
                price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                p_resp = requests.get(price_url, headers=headers, timeout=30)
                price_items = p_resp.json().get("items", []) if p_resp.status_code == 200 else []

                def get_price_cost(cname, sname):
                    for it in price_items:
                        if it.get("color") == cname and it.get("size") == sname:
                            prices = it.get("prices", []) or []
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                i_resp = requests.get(inv_url, headers=headers, timeout=30)
                inv_items = i_resp.json().get("items", []) if i_resp.status_code == 200 else []

                def get_sku(cname, sname):
                    for it in inv_items:
                        if it.get("color") == cname and it.get("size") == sname:
                            return it.get("sku") or ""
                    return ""

                for variant in template.product_variant_ids:
                    cval = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == color_attr.id
                    )
                    sval = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.id == size_attr.id
                    )
                    cname = cval.name if cval else ""
                    sname = sval.name if sval else ""
                    sku = get_sku(cname, sname)
                    cost = get_price_cost(cname, sname)
                    if sku:
                        variant.default_code = sku
                    variant.standard_price = cost
                    variant.lst_price = round(cost * 2, 2) if cost else 9.99
                    _logger.info(f"🧵 Variante {variant.default_code} - {variant.name} - {cost}€")
            except Exception as e:
                _logger.warning(f"⚠️ Precios/SKUs {catalog_ref}: {e}")

        if not any_valid:
            _logger.info(f"✅ Página {page_number} sin novedades.")
        icp.set_param("toptex_last_page", str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # -------------------------------------------------
    # Stock (ya probado en tu entorno) -> WH/Stock
    # -------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env["ir.config_parameter"].sudo()
        proxy_url = icp.get_param("toptex_proxy_url")
        api_key = icp.get_param("toptex_api_key")
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")

        # Auth
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(
            auth_url, json={"username": username, "password": password}, headers=headers, timeout=20
        ).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Product = self.env["product.product"]
        Quant = self.env["stock.quant"]

        # Siempre la ubicación principal del almacén principal
        warehouse = self.env["stock.warehouse"].search([], limit=1)
        location = warehouse.lot_stock_id if warehouse else self.env["stock.location"].search(
            [("usage", "=", "internal")], limit=1
        )
        if not location:
            _logger.warning("❌ No se encontró ubicación interna para crear quants.")
            return

        for variant in Product.search([("default_code", "!=", False)]):
            if variant.type != "consu" or not variant.product_tmpl_id.is_storable:
                continue

            sku = variant.default_code
            inv_url = f"{proxy_url}/v3/products/{sku}/inventory"
            r = requests.get(inv_url, headers=headers, timeout=20)
            if r.status_code != 200:
                _logger.warning(f"❌ Inventario {sku}: {r.status_code} {r.text}")
                continue

            try:
                js = r.json()
                warehouses = js.get("warehouses", []) if isinstance(js, dict) else (
                    js[0].get("warehouses", []) if isinstance(js, list) and js else []
                )
                stock = 0
                for wh in warehouses:
                    if isinstance(wh, dict) and wh.get("id") == "toptex":
                        stock = int(wh.get("stock", 0))
                        break
            except Exception as e:
                _logger.error(f"❌ JSON inventario {sku}: {e}")
                stock = 0

            quant = Quant.search([("product_id", "=", variant.id), ("location_id", "=", location.id)], limit=1)
            if quant:
                quant.write({"quantity": stock, "inventory_quantity": stock})
            else:
                Quant.create(
                    {"product_id": variant.id, "location_id": location.id, "quantity": stock, "inventory_quantity": stock}
                )
            _logger.info(f"✅ stock.quant creado/actualizado para {sku} en WH/Stock: {stock}")

    # -------------------------------------------------
    # Imágenes por variante (nuevo, robusto con reanudación)
    # -------------------------------------------------
    def sync_variant_images_from_api(self, batch_size=300):
        icp = self.env["ir.config_parameter"].sudo()
        proxy = icp.get_param("toptex_proxy_url")
        api_key = icp.get_param("toptex_api_key")
        username = icp.get_param("toptex_username")
        password = icp.get_param("toptex_password")

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(
            auth_url, json={"username": username, "password": password}, headers=headers, timeout=20
        ).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = token.strip()

        # Reanudación + tiempo máximo
        offset = int(icp.get_param("toptex_img_offset") or 0)
        max_seconds = int(icp.get_param("toptex_img_max_seconds") or 840)  # ~14 min
        t0 = time.monotonic()

        Product = self.env["product.product"]
        all_ids = Product.search([("default_code", "!=", False)], order="id asc")
        if not all_ids:
            _logger.info("⛔ No hay variantes con SKU para procesar.")
            icp.set_param("toptex_img_offset", "0")
            return

        # Rango a procesar
        to_process = all_ids[offset : offset + batch_size]
        if not to_process:
            offset = 0
            to_process = all_ids[:batch_size]

        # Atributo color
        color_attr = self.env["product.attribute"].search([("name", "ilike", "color")], limit=1)

        processed = 0
        for variant in to_process:
            # Control de timeout
            if time.monotonic() - t0 > max_seconds:
                _logger.info(f"⏱️ Tiempo límite alcanzado, guardando offset y saliendo.")
                break

            sku = variant.default_code
            color_name = ""
            if color_attr:
                pav = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.id == color_attr.id
                )
                color_name = (pav.name or "").strip()

            # Consulta por SKU
            url = f"{proxy}/v3/products?sku={sku}&usage_right=b2b_b2c"
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code != 200:
                _logger.warning(f"❌ {sku}: {r.status_code} {r.text}")
                offset += 1
                processed += 1
                continue

            # Parseo robusto
            try:
                js = r.json()
            except Exception as e:
                _logger.warning(f"❌ JSON inválido para {sku}: {e}")
                offset += 1
                processed += 1
                continue

            item = js[0] if isinstance(js, list) and js else (js if isinstance(js, dict) else None)
            if not item:
                _logger.warning(f"✖️ Sin datos para SKU {sku}, saltando.")
                offset += 1
                processed += 1
                continue

            def _best_packshot(rec):
                """Devuelve mejor URL de packshot FACE o imagen alternativa."""
                # 1) packshots directos
                ps = rec.get("packshots") or {}
                if isinstance(ps, dict):
                    face = ps.get("FACE") or ps.get("face") or {}
                    u = face.get("url_packshot") or face.get("url")
                    if u:
                        return u
                # 2) por colores
                for c in rec.get("colors", []) or []:
                    cname = (c.get("colors") or {}).get("es") or (c.get("colors") or {}).get("en") or c.get("color") or ""
                    if not color_name or (cname and cname.strip().lower() == color_name.lower()):
                        cps = c.get("packshots") or {}
                        face = cps.get("FACE") or cps.get("face") or {}
                        u = face.get("url_packshot") or face.get("url")
                        if u:
                            return u
                # 3) fallback a images
                for im in rec.get("images", []) or []:
                    u = im.get("url_image") or im.get("url")
                    if u:
                        return u
                return None

            img_url = _best_packshot(item)
            if img_url and not img_url.startswith("http"):
                if img_url.startswith("/"):
                    img_url = "https://cdn.toptex.com" + img_url
                else:
                    img_url = f"{proxy}{img_url}"

            if not img_url:
                _logger.warning(f"❌ Sin packshot para SKU/color: {sku} / {color_name or '-'} . Saltando.")
                offset += 1
                processed += 1
                continue

            img_b64 = get_image_binary_from_url(img_url)
            if img_b64:
                try:
                    variant.image_1920 = img_b64
                    self.env.cr.commit()  # aseguramos persistencia si el server action corta
                    _logger.info(f"✅ Imagen asignada a variante {sku} ({color_name or '-'})")
                except Exception as e:
                    _logger.warning(f"⚠️ No se pudo escribir imagen en {sku}: {e}")
            else:
                _logger.warning(f"❌ Falló descarga de imagen para {sku}")

            offset += 1
            processed += 1

        # Persistimos offset (reanudación)
        icp.set_param("toptex_img_offset", str(offset))
        _logger.info(f"🧾 IMG offset guardado: {offset} | Procesadas: {processed} | Tiempo: {int(time.monotonic()-t0)}s")