# -*- coding: utf-8 -*-
import io
import re
import time
import base64
import logging
import requests
from requests import Session
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

def get_image_binary_from_url(url, session: Session = None):
    """Descarga imagen y devuelve base64 JPG."""
    try:
        _logger.debug(f"🖼️ Descargando imagen desde {url}")
        s = session or requests
        r = s.get(url, stream=True, timeout=15)
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
        _logger.debug(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.debug(f"❌ Error al procesar imagen: {e}")
    return None

def _unit_price_from_tiers(prices):
    """Devuelve el precio del tramo con menor cantidad (quantity/minQuantity)."""
    best = None
    best_q = None
    for p in prices or []:
        if not isinstance(p, dict):
            continue
        q = p.get('quantity') or p.get('minQuantity') or p.get('min_quantity') or 0
        try:
            q = int(q)
        except Exception:
            q = 0
        try:
            pr = float(p.get('price', 0.0))
        except Exception:
            pr = 0.0
        if best_q is None or q < best_q:
            best_q, best = q, pr
    return float(best or 0.0)

def _norm_ref(s):
    """Normaliza referencias para evitar duplicados por mayúsculas/espacios."""
    return (s or "").strip().upper()


# ===================== Modelo =====================

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ---------------------------------------------------------------------
    # Productos (paginado 50): DEDUP + variantes nuevas + coste solo si hay SKU
    # AJUSTES: Session reutilizable + offset garantizado + logs contenidos
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

        # Session para acelerar todas las llamadas
        session = requests.Session()
        session.headers.update({"x-api-key": api_key, "Content-Type": "application/json"})

        auth = session.post(f"{proxy}/v3/authenticate",
                            json={"username": username, "password": password},
                            timeout=20)
        if auth.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth.status_code} - {auth.text}")
        token = (auth.json() or {}).get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        session.headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param('toptex_last_page') or 1)
        next_page = page_number + 1
        page_size = 50

        try:
            url = f"{proxy}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
            r = session.get(url, timeout=45)
            if r.status_code != 200:
                _logger.warning(f"❌ Error en página {page_number}: {r.text}")
                # aun así avanzamos para no repetir
                icp.set_param('toptex_last_page', str(next_page))
                return

            batch = r.json()
            if isinstance(batch, dict) and "items" in batch:
                batch = batch["items"]

            # AVANZAR OFFSET ***ANTES*** DE PROCESAR (garantiza progreso)
            icp.set_param('toptex_last_page', str(next_page))
            _logger.info(f"OFFSET PRE-AVANZADO: {next_page}")

            # fin de catálogo: reiniciar a 1
            if not batch:
                _logger.info("✅ Página vacía. Fin de catálogo detectado. Reinicio a página 1 para próximo ciclo.")
                icp.set_param('toptex_last_page', '1')
                return

            Attr    = self.env['product.attribute']
            AttrVal = self.env['product.attribute.value']

            color_attr = Attr.search([('name','=','Color')], limit=1) or Attr.create({'name':'Color'})
            size_attr  = Attr.search([('name','=','Talla')], limit=1) or Attr.create({'name':'Talla'})

            def _ensure_vals(attr, names):
                out = {}
                for n in names:
                    if not n:
                        continue
                    v = AttrVal.search([('name','=',n), ('attribute_id','=',attr.id)], limit=1) \
                        or AttrVal.create({'name': n, 'attribute_id': attr.id})
                    out[n] = v
                return out

            def _cost_by_sku(sku):
                """Obtiene coste por SKU; sin fallback a catálogo."""
                try:
                    r1 = session.get(f"{proxy}/v3/products/{sku}/price", timeout=12)
                    if r1.status_code == 200:
                        js = r1.json() or {}
                        if isinstance(js, dict) and isinstance(js.get('prices'), list):
                            return _unit_price_from_tiers(js['prices'])
                        if isinstance(js, list):
                            for it in js:
                                if isinstance(it, dict) and isinstance(it.get('prices'), list):
                                    val = _unit_price_from_tiers(it['prices'])
                                    if val:
                                        return val
                except Exception as e:
                    _logger.debug(f"Precio SKU(path) {sku}: {e}")

                try:
                    r2 = session.get(f"{proxy}/v3/products/price?sku={sku}", timeout=12)
                    if r2.status_code == 200:
                        js2 = r2.json() or {}
                        if isinstance(js2, dict) and isinstance(js2.get('items'), list) and js2['items']:
                            return _unit_price_from_tiers(js2['items'][0].get('prices') or [])
                        if isinstance(js2, list):
                            for it in js2:
                                if isinstance(it, dict) and isinstance(it.get('prices'), list):
                                    val = _unit_price_from_tiers(it['prices'])
                                    if val:
                                        return val
                except Exception as e:
                    _logger.debug(f"Precio SKU(query) {sku}: {e}")

                return 0.0

            created = existed = set_sku = set_cost = set_img = errors = 0

            for data in batch:
                # Nunca permitir que un producto bloquee el resto
                try:
                    if not isinstance(data, dict):
                        continue

                    catalog_ref = (data.get("catalogReference") or "").strip()
                    if not catalog_ref:
                        continue

                    name_data = data.get("designation") or {}
                    designation = (name_data.get("es") or name_data.get("en") or "Producto sin nombre").replace("TopTex", "").strip()
                    full_name = f"{catalog_ref} {designation}".strip()

                    _logger.debug(f"▶ Procesando {catalog_ref} …")

                    # DEDUP: por default_code o por nombre que empieza por la ref
                    tmpl = self.search([('default_code', '=', catalog_ref)], limit=1)
                    if not tmpl:
                        tmpl = self.search([('name', 'ilike', catalog_ref + ' %')], limit=1)

                    # recolectar colores/tallas del JSON
                    colors = data.get("colors") or []
                    all_colors, all_sizes = set(), set()
                    for c in colors:
                        cname = (c.get("colors") or {}).get("es") or (c.get("colors") or {}).get("en") or ""
                        if cname:
                            all_colors.add(cname)
                        for s in c.get("sizes") or []:
                            all_sizes.add(s.get("size"))

                    color_vals = _ensure_vals(color_attr, all_colors)
                    size_vals  = _ensure_vals(size_attr,  all_sizes)

                    if tmpl:
                        existed += 1
                        # === EXISTE: ampliar atributos y generar variantes nuevas ===
                        line_color = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.id == color_attr.id)
                        line_size  = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id.id == size_attr.id)

                        have_colors = set(line_color.value_ids.mapped('name')) if line_color else set()
                        have_sizes  = set(line_size.value_ids.mapped('name'))  if line_size  else set()

                        add_color_ids = [color_vals[n].id for n in all_colors if n not in have_colors]
                        add_size_ids  = [size_vals[n].id  for n in all_sizes  if n not in have_sizes]

                        if add_color_ids:
                            if line_color:
                                line_color.write({'value_ids': [(4, vid) for vid in add_color_ids]})
                            else:
                                self.env['product.template.attribute.line'].create({
                                    'product_tmpl_id': tmpl.id,
                                    'attribute_id': color_attr.id,
                                    'value_ids': [(6, 0, add_color_ids)]
                                })
                        if add_size_ids:
                            if line_size:
                                line_size.write({'value_ids': [(4, vid) for vid in add_size_ids]})
                            else:
                                self.env['product.template.attribute.line'].create({
                                    'product_tmpl_id': tmpl.id,
                                    'attribute_id': size_attr.id,
                                    'value_ids': [(6, 0, add_size_ids)]
                                })
                        # Forzar generación de variantes nuevas
                        try:
                            tmpl._create_variant_ids()
                            tmpl.invalidate_cache(['product_variant_ids'])
                        except Exception:
                            pass

                    else:
                        # === NO EXISTE: crear template normal ===
                        description = (data.get("description") or {}).get("es") or (data.get("description") or {}).get("en") or ""
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
                            created += 1
                            _logger.info(f"✅ Producto creado: {catalog_ref} | {full_name}")
                        except Exception as e:
                            errors += 1
                            _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                            continue

                        # Imagen principal (solo si el template no tiene)
                        try:
                            if not tmpl.image_1920:
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
                                    img_b64 = get_image_binary_from_url(main_url, session=session)
                                    if img_b64:
                                        tmpl.image_1920 = img_b64
                                        set_img += 1
                        except Exception as e:
                            _logger.debug(f"⚠️ No se pudo asignar imagen al template {catalog_ref}: {e}")

                    # === Asignar SKU a variantes sin SKU; coste solo si hay SKU ===
                    try:
                        # Traer inventario una vez por ref
                        inv_items = []
                        rinv = session.get(f"{proxy}/v3/products/inventory?catalog_reference={catalog_ref}",
                                           timeout=12)
                        if rinv.status_code == 200:
                            inv_items = (rinv.json() or {}).get("items", []) or []

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

                            if not v.default_code:
                                sku = get_sku(cname, sname)
                                if sku:
                                    v.default_code = sku
                                    set_sku += 1
                                    # Coste SOLO si hay SKU
                                    if (not v.standard_price) or float(v.standard_price) == 0.0:
                                        cost = _cost_by_sku(sku)
                                        if cost:
                                            v.standard_price = cost
                                            if not v.lst_price:
                                                v.lst_price = round(cost*2, 2)
                                            set_cost += 1

                    except Exception as e:
                        errors += 1
                        _logger.debug(f"⚠️ Error asignando SKUs/costes {catalog_ref}: {e}")

                    _logger.debug(f"✔ Procesado {catalog_ref}")

                except Exception as e:
                    errors += 1
                    _logger.error(f"❌ Error procesando ref: {data.get('catalogReference')}: {e}")
                    # seguir con el siguiente producto SIEMPRE
                    continue

            _logger.info(f"Resumen página {page_number}: creados={created}, existentes={existed}, "
                         f"sku_asignados={set_sku}, costes_actualizados={set_cost}, imagenes={set_img}, errores={errors}")

        finally:
            # Garantiza avance aunque haya fallos en mitad del proceso
            if str(icp.get_param('toptex_last_page') or '') != str(next_page):
                icp.set_param('toptex_last_page', str(next_page))
            _logger.info(f"OFFSET ASEGURADO: {next_page}")

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

            quant = self.env['stock.quant'].search([('product_id','=',v.id), ('location_id','=',location.id)], limit=1)
            if quant:
                quant.write({'quantity': stock, 'inventory_quantity': stock})
            else:
                self.env['stock.quant'].create({'product_id': v.id, 'location_id': location.id,
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
                _logger.debug(f"❌ Sin packshot para SKU/color: {sku} ({color_name}).")
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

    # ---------------------------------------------------------------------
    # Server Action: precio de coste POR SKU (sin fallback si no hay SKU)
    # ---------------------------------------------------------------------
    def sync_cost_price_from_api(self):
        """
        Actualiza standard_price (coste) de cada variante por SKU:
          1) /v3/products/{sku}/price
          2) /v3/products/price?sku=SKU
        Si no hay SKU o no hay precio por SKU -> NO toca el coste.
        No modifica lst_price.
        """
        icp = self.env['ir.config_parameter'].sudo()
        proxy    = icp.get_param('toptex_proxy_url')
        api_key  = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        if not all([proxy, api_key, username, password]):
            _logger.error("❌ Falta configuración para precios de coste.")
            return

        session = requests.Session()
        session.headers.update({"x-api-key": api_key, "Content-Type":"application/json"})
        try:
            token = session.post(f"{proxy}/v3/authenticate",
                                 json={"username": username, "password": password},
                                 timeout=20).json().get("token")
        except Exception as e:
            _logger.error(f"❌ Error autenticando (coste): {e}")
            return
        if not token:
            _logger.error("❌ Token inválido (coste).")
            return
        session.headers["x-toptex-authorization"] = token.strip()

        last_var_id = int(icp.get_param('toptex_cost_last_var_id') or 0)
        budget      = int(icp.get_param('toptex_cost_time_budget') or 900)  # 15 min
        start       = time.monotonic()

        Variant = self.env['product.product']

        variants = Variant.search([('id','>',last_var_id)], order='id', limit=6000)
        if not variants:
            variants = Variant.search([], order='id', limit=6000)
            last_var_id = 0

        new_last = last_var_id

        def _cost_by_sku(sku):
            try:
                r1 = session.get(f"{proxy}/v3/products/{sku}/price", timeout=12)
                if r1.status_code == 200:
                    js = r1.json() or {}
                    if isinstance(js, dict) and isinstance(js.get('prices'), list):
                        return _unit_price_from_tiers(js['prices'])
                    if isinstance(js, list):
                        for it in js:
                            if isinstance(it, dict) and isinstance(it.get('prices'), list):
                                val = _unit_price_from_tiers(it['prices'])
                                if val:
                                    return val
            except Exception as e:
                _logger.debug(f"SKU price(path) {sku}: {e}")
            try:
                r2 = session.get(f"{proxy}/v3/products/price?sku={sku}", timeout=12)
                if r2.status_code == 200:
                    js2 = r2.json() or {}
                    if isinstance(js2, dict) and isinstance(js2.get('items'), list) and js2['items']:
                        return _unit_price_from_tiers(js2['items'][0].get('prices') or [])
                    if isinstance(js2, list):
                        for it in js2:
                            if isinstance(it, dict) and isinstance(it.get('prices'), list):
                                val = _unit_price_from_tiers(it['prices'])
                                if val:
                                    return val
            except Exception as e:
                _logger.debug(f"SKU price(query) {sku}: {e}")
            return 0.0

        for v in variants:
            new_last = v.id
            if v.type != 'consu' or not v.product_tmpl_id.is_storable:
                continue

            sku = (v.default_code or "").strip()
            if not sku:
                continue  # sin SKU: no tocar coste

            cost = _cost_by_sku(sku)
            if cost:
                try:
                    v.with_context(disable_standard_price_constraint=True).write({'standard_price': float(cost)})
                    _logger.info(f"💰 Coste actualizado por SKU: {sku} -> {float(cost)}")
                except Exception as e:
                    _logger.warning(f"⚠️ No se pudo actualizar coste SKU {sku}: {e}")

            if time.monotonic() - start > budget:
                icp.set_param('toptex_cost_last_var_id', str(new_last))
                _logger.warning(f"⏱️ Tiempo límite alcanzado (coste SKU). Guardado offset var {new_last} y saliendo.")
                return

        icp.set_param('toptex_cost_last_var_id', str(new_last if variants else 0))
        _logger.info(f"COST offset guardado (var): {new_last if variants else 0}")