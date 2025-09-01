# -*- coding: utf-8 -*-
import io
import re
import time
import base64
import logging
import requests
from PIL import Image
from difflib import get_close_matches

from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ===================== Utilidades =====================

def _normalize_color_name(name: str) -> str:
    """Normaliza nombres de color para mejorar el matching."""
    if not name:
        return ""
    s = name.strip().lower()
    s = re.sub(r"\(.*?\)", "", s)            # quita '(...)'
    s = s.split("/")[0]                      # quita after '/'
    rep = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","-":" ","_":" "}
    for k,v in rep.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s).strip()
    # alias típicos
    alias = {"grey":"gray","graphite grey":"graphite gray","light grey":"light gray"}
    return alias.get(s, s)

def _choose_packshot_url(packshots):
    """Elige el mejor packshot disponible según prioridad."""
    if not isinstance(packshots, dict):
        return None
    d = {str(k).upper(): v for k, v in packshots.items() if isinstance(k, str)}
    order = ["FACE","FRONT","3Q","SIDE","LEFT","RIGHT","BACK","PACKSHOT","FLAT","DEFAULT","MAIN"]
    for key in order:
        node = d.get(key)
        if isinstance(node, dict) and node.get("url_packshot"):
            return node["url_packshot"]
    # cualquiera válido
    for node in d.values():
        if isinstance(node, dict) and node.get("url_packshot"):
            return node["url_packshot"]
    return None

def get_image_binary_from_url(url):
    """Descarga imagen y devuelve base64 JPG."""
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code == 200 and "image" in (r.headers.get("Content-Type","")):
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ("RGBA","LA"):
                bg = Image.new("RGB", img.size, (255,255,255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return base64.b64encode(buf.getvalue())
        _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen: {e}")
    return None


# ===================== Modelo =====================

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ---------------------------------------------------------------------
    # Productos (no tocar lo que ya funciona; mantenemos patrón existente)
    # ---------------------------------------------------------------------
    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key  = icp.get_param('toptex_api_key')
        proxy    = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth = requests.post(f"{proxy}/v3/authenticate",
                             json={"username": username, "password": password},
                             headers=headers, timeout=30)
        if auth.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth.status_code} - {auth.text}")
        token = (auth.json() or {}).get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        url = f"{proxy}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code != 200:
            _logger.warning(f"❌ Error en página {page_number}: {r.text}")
            return

        batch = r.json()
        if isinstance(batch, dict) and "items" in batch:
            batch = batch["items"]
        if not batch:
            _logger.info("✅ Sin productos nuevos en esta página.")
            icp.set_param('toptex_last_page', str(page_number + 1))
            return

        processed_refs = set(self.env['product.template'].search([]).mapped('default_code'))
        Attr = self.env['product.attribute']
        AttrVal = self.env['product.attribute.value']

        for data in batch:
            if not isinstance(data, dict):
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref or catalog_ref in processed_refs:
                continue

            name_data = data.get("designation") or {}
            name = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {name}".strip()
            description = (data.get("description") or {}).get("es") or (data.get("description") or {}).get("en") or ""

            # atributos
            colors = data.get("colors") or []
            all_colors, all_sizes = set(), set()
            for c in colors:
                cname = (c.get("colors") or {}).get("es") or (c.get("colors") or {}).get("en") or ""
                if cname:
                    all_colors.add(cname)
                for s in c.get("sizes") or []:
                    all_sizes.add(s.get("size"))

            color_attr = Attr.search([('name','=','Color')], limit=1) or Attr.create({'name':'Color'})
            size_attr  = Attr.search([('name','=','Talla')], limit=1) or Attr.create({'name':'Talla'})

            color_vals = {}
            for cname in all_colors:
                if not cname: continue
                val = AttrVal.search([('name','=',cname),('attribute_id','=',color_attr.id)], limit=1) \
                      or AttrVal.create({'name': cname, 'attribute_id': color_attr.id})
                color_vals[cname] = val

            size_vals = {}
            for sname in all_sizes:
                if not sname: continue
                val = AttrVal.search([('name','=',sname),('attribute_id','=',size_attr.id)], limit=1) \
                      or AttrVal.create({'name': sname, 'attribute_id': size_attr.id})
                size_vals[sname] = val

            attribute_lines = [
                {'attribute_id': color_attr.id, 'value_ids': [(6,0,[v.id for v in color_vals.values()])]},
                {'attribute_id': size_attr.id,  'value_ids': [(6,0,[v.id for v in size_vals.values()])]},
            ]

            vals = {
                'name': full_name,
                'default_code': catalog_ref,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0,0,l) for l in attribute_lines],
            }
            try:
                tmpl = self.create(vals)
                processed_refs.add(catalog_ref)
                _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
            except Exception as e:
                _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                continue

            # imagen principal del template (no toca variantes)
            try:
                main_url = None
                for img in (data.get("images") or []):
                    if isinstance(img, dict) and img.get("url_image"):
                        main_url = img["url_image"]; break
                if not main_url:
                    for c in (data.get("colors") or []):
                        pic = _choose_packshot_url(c.get("packshots") or {})
                        if pic:
                            main_url = pic; break
                if main_url:
                    img_b64 = get_image_binary_from_url(main_url)
                    if img_b64:
                        tmpl.image_1920 = img_b64
            except Exception as e:
                _logger.warning(f"⚠️ No se pudo asignar imagen al template {catalog_ref}: {e}")

            # precios + sku
            try:
                price_items = []
                rprice = requests.get(f"{proxy}/v3/products/price?catalog_reference={catalog_ref}",
                                      headers=headers, timeout=30)
                if rprice.status_code == 200:
                    price_items = (rprice.json() or {}).get("items", []) or []

                inv_items = []
                rinv = requests.get(f"{proxy}/v3/products/inventory?catalog_reference={catalog_ref}",
                                    headers=headers, timeout=30)
                if rinv.status_code == 200:
                    inv_items = (rinv.json() or {}).get("items", []) or []

                def get_cost(cn, sn):
                    for it in price_items:
                        if it.get("color")==cn and it.get("size")==sn:
                            prices = it.get("prices") or []
                            if prices:
                                return float(prices[0].get("price",0.0))
                    return 0.0

                def get_sku(cn, sn):
                    for it in inv_items:
                        if it.get("color")==cn and it.get("size")==sn:
                            return it.get("sku") or ""
                    return ""

                for v in tmpl.product_variant_ids:
                    cval = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.id==color_attr.id)
                    sval = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.id==size_attr.id)
                    cname = cval.name if cval else ""
                    sname = sval.name if sval else ""
                    sku = get_sku(cname, sname)
                    cost = get_cost(cname, sname)
                    if sku:
                        v.default_code = sku
                    v.standard_price = cost
                    v.lst_price = round(cost*2, 2) if cost else 9.99
            except Exception as e:
                _logger.warning(f"⚠️ Error en precios/SKUs de {catalog_ref}: {e}")

        icp.set_param('toptex_last_page', str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO: {page_number + 1}")

    # ---------------------------------------------------------------------
    # Stock: bloque “que funcionaba” + offset + 15 min (no toca lo demás)
    # ---------------------------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy    = icp.get_param('toptex_proxy_url')
        api_key  = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        headers = {"x-api-key": api_key, "Content-Type":"application/json"}
        token = requests.post(f"{proxy}/v3/authenticate",
                              json={"username": username, "password": password},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Product = self.env['product.product']
        Quant   = self.env['stock.quant']
        wh = self.env['stock.warehouse'].search([], limit=1)
        location = wh.lot_stock_id if wh else self.env['stock.location'].search([('usage','=','internal')], limit=1)
        if not location:
            _logger.warning("❌ No hay ubicación interna para crear quants.")
            return

        last_id = int(icp.get_param('toptex_stock_last_id') or 0)
        budget  = int(icp.get_param('toptex_stock_time_budget') or 900)  # 15 min por defecto
        start   = time.monotonic()

        variants = Product.search([('id','>',last_id), ('default_code','!=',False)], order='id', limit=5000)
        if not variants:
            variants = Product.search([('default_code','!=',False)], order='id', limit=5000)
            last_id = 0

        new_last = last_id
        for v in variants:
            new_last = v.id
            if v.type != 'consu' or not v.product_tmpl_id.is_storable:
                continue

            sku = v.default_code
            r = requests.get(f"{proxy}/v3/products/{sku}/inventory", headers=headers, timeout=20)
            if r.status_code != 200:
                _logger.warning(f"❌ Inventario {sku}: {r.status_code} {r.text}")
                continue

            try:
                js = r.json()
                warehouses = js.get("warehouses", []) if isinstance(js, dict) else (js[0].get("warehouses", []) if isinstance(js, list) and js else [])
                stock = 0
                for whrow in warehouses:
                    if isinstance(whrow, dict) and whrow.get("id") == "toptex":
                        stock = int(whrow.get("stock", 0)); break
            except Exception as e:
                _logger.error(f"❌ JSON inventario {sku}: {e}")
                stock = 0

            quant = Quant.search([('product_id','=',v.id), ('location_id','=',location.id)], limit=1)
            if quant:
                quant.write({'quantity': stock, 'inventory_quantity': stock})
            else:
                Quant.create({'product_id': v.id, 'location_id': location.id,
                              'quantity': stock, 'inventory_quantity': stock})
            _logger.info(f"✅ stock.quant creado/actualizado para {sku} en WH/Stock: {stock}")

            if time.monotonic() - start > budget:
                icp.set_param('toptex_stock_last_id', str(new_last))
                _logger.warning(f"⏱️ Tiempo límite alcanzado (stock). Guardado offset {new_last} y saliendo.")
                return

        icp.set_param('toptex_stock_last_id', str(new_last if variants else 0))
        _logger.info(f"STOCK offset guardado: {new_last if variants else 0}")

    # ---------------------------------------------------------------------
    # Imágenes por variante: SOLO ajuste final (SKU + color) + offset/timeout
    # ---------------------------------------------------------------------
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy    = icp.get_param('toptex_proxy_url')
        api_key  = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        headers = {"x-api-key": api_key, "Content-Type":"application/json"}
        token = requests.post(f"{proxy}/v3/authenticate",
                              json={"username": username, "password": password},
                              headers=headers, timeout=30).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Variant = self.env['product.product']
        last_id = int(icp.get_param('toptex_img_last_id') or 0)
        budget  = int(icp.get_param('toptex_img_time_budget') or 900)  # 15 min por defecto
        start   = time.monotonic()

        variants = Variant.search([('id','>',last_id), ('default_code','!=',False)], order='id', limit=6000)
        if not variants:
            variants = Variant.search([('default_code','!=',False)], order='id', limit=6000)
            last_id = 0

        new_last = last_id

        def _extract_color_map(product_json):
            cmap = {}
            if not isinstance(product_json, dict):
                return cmap
            for c in (product_json.get("colors") or []):
                col = (c.get("colors") or {}).get("es") or (c.get("colors") or {}).get("en") or ""
                url = _choose_packshot_url(c.get("packshots") or {})
                if not url:
                    for im in (c.get("images") or []):
                        if isinstance(im, dict) and im.get("url_image"):
                            url = im["url_image"]; break
                if col and url:
                    cmap[_normalize_color_name(col)] = url
            return cmap

        def _fetch_by_sku(sku):
            try:
                r = requests.get(f"{proxy}/v3/products?sku={sku}&usage_right=b2b_b2c",
                                 headers=headers, timeout=25)
                data = r.json() if r.status_code == 200 else None
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                _logger.warning(f"❌ Error SKU fetch ({sku}): {e}")
            return None

        def _fetch_by_catalog(catref):
            try:
                r = requests.get(f"{proxy}/v3/products?catalog_reference={catref}&usage_right=b2b_b2c",
                                 headers=headers, timeout=25)
                data = r.json() if r.status_code == 200 else None
                if isinstance(data, list) and data:
                    return data[0]
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                _logger.warning(f"❌ Error catalog fetch ({catref}): {e}")
            return None

        for v in variants:
            new_last = v.id
            pav = v.product_template_attribute_value_ids.filtered(lambda x: x.attribute_id.name.lower()=='color')
            color_name = pav.name if pav else ""
            norm_color = _normalize_color_name(color_name)
            sku = v.default_code
            catref = v.product_tmpl_id.default_code or ""

            # 1) buscar por SKU
            pack_url = None
            data = _fetch_by_sku(sku)
            cmap = _extract_color_map(data or {})
            if cmap:
                pack_url = cmap.get(norm_color)
                if not pack_url:
                    close = get_close_matches(norm_color, list(cmap.keys()), n=1, cutoff=0.85)
                    if close:
                        pack_url = cmap.get(close[0])

            # 2) fallback por catalog_reference
            if not pack_url and catref:
                data2 = _fetch_by_catalog(catref)
                cmap2 = _extract_color_map(data2 or {})
                if cmap2:
                    pack_url = cmap2.get(norm_color)
                    if not pack_url:
                        close = get_close_matches(norm_color, list(cmap2.keys()), n=1, cutoff=0.85)
                        if close:
                            pack_url = cmap2.get(close[0])

            if not pack_url:
                _logger.warning(f"❌ Sin packshot para SKU/color: {sku} ({color_name}). Saltando.")
            else:
                img_b64 = get_image_binary_from_url(pack_url)
                if img_b64:
                    try:
                        v.write({'image_1920': img_b64})
                        _logger.info(f"✅ Imagen asignada a variante {sku} ({color_name})")
                    except Exception as e:
                        _logger.warning(f"⚠️ No se pudo guardar imagen de {sku}: {e}")

            # control de tiempo / offset
            if time.monotonic() - start > budget:
                icp.set_param('toptex_img_last_id', str(new_last))
                _logger.warning(f"⏱️ Tiempo límite alcanzado (img). Guardado offset {new_last} y saliendo.")
                return

        icp.set_param('toptex_img_last_id', str(new_last if variants else 0))
        _logger.info(f"IMG offset guardado: {new_last if variants else 0}")