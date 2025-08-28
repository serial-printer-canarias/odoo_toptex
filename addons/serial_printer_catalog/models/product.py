# -*- coding: utf-8 -*-
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------------------------
# Util: descargar imagen URL
# ---------------------------
def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        r = requests.get(url, stream=True, timeout=15)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            img = Image.open(io.BytesIO(r.content))
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return base64.b64encode(buf.getvalue())
        _logger.warning(f"⚠️ Respuesta no-imagen para {url} ({r.status_code})")
    except Exception as e:
        _logger.warning(f"❌ Error procesando imagen {url}: {e}")
    return None

def _rgb_to_hex(rgb):
    """rgb puede venir como {'r': 12, 'g': 34, 'b': 56} o '#AABBCC'."""
    if isinstance(rgb, dict):
        r = max(0, min(255, int(rgb.get('r', 0))))
        g = max(0, min(255, int(rgb.get('g', 0))))
        b = max(0, min(255, int(rgb.get('b', 0))))
        return f"#{r:02X}{g:02X}{b:02X}"
    if isinstance(rgb, str) and rgb.strip():
        val = rgb.strip()
        if not val.startswith("#") and len(val) in (3, 6):
            # 'ABC' o 'AABBCC'
            val = f"#{val}"
        return val
    return False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------
    # Productos y variantes (igual que venías usando)
    # -------------------------------------------------
    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key  = icp.get_param('toptex_api_key')
        proxy    = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy]):
            raise UserError("❌ Faltan credenciales/parámetros de TopTex.")

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token.strip()

        page_number = int(icp.get_param('toptex_last_page') or 1)
        page_size = 50

        url = f"{proxy}/v3/products/all?usage_right=b2b_b2c&page_number={page_number}&page_size={page_size}"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            _logger.warning(f"❌ Error página {page_number}: {resp.text}")
            return

        batch = resp.json()
        if isinstance(batch, dict):
            batch = batch.get("items") or []
        if not batch:
            _logger.info("✅ Sin productos nuevos en esta página.")
            icp.set_param('toptex_last_page', str(page_number + 1))
            return

        ProductTmpl = self.env['product.template']
        Attr = self.env['product.attribute']
        AttrVal = self.env['product.attribute.value']

        # Atributos Color / Talla
        color_attr = Attr.search([('name', '=', 'Color')], limit=1) or Attr.create({'name': 'Color'})
        size_attr  = Attr.search([('name', '=', 'Talla')], limit=1) or Attr.create({'name': 'Talla'})
        has_html_color = 'html_color' in AttrVal._fields

        existing_refs = set(ProductTmpl.search([]).mapped('default_code'))
        created_any = False

        for data in batch:
            if not isinstance(data, dict):
                continue

            catalog_ref = data.get("catalogReference")
            if not catalog_ref:
                continue
            if catalog_ref in existing_refs:
                _logger.info(f"⏩ Ya existe: {catalog_ref}")
                continue

            # Nombre / desc
            name_i18n = data.get("designation", {}) or {}
            base_name = (name_i18n.get("es") or name_i18n.get("en") or "Producto").replace("TopTex", "").strip()
            full_name = f"{catalog_ref} {base_name}".strip()
            description = (data.get("description", {}) or {}).get("es") or (data.get("description", {}) or {}).get("en") or ""

            # Colores / tallas desde la ficha
            colors = data.get("colors", []) or []
            color_vals_map = {}
            size_vals_map  = {}

            for c in colors:
                # Etiqueta color y rgb/hex
                label = (c.get("colors", {}) or {}).get("es") or (c.get("colors", {}) or {}).get("en") or ""
                if not label:
                    continue
                # Crear/obtener valor de atributo Color
                val = AttrVal.search([('name', '=', label), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    vals = {'name': label, 'attribute_id': color_attr.id}
                    # Guardar swatch si viene
                    hex_col = _rgb_to_hex(c.get("rgb"))
                    if has_html_color and hex_col:
                        vals['html_color'] = hex_col
                    val = AttrVal.create(vals)
                else:
                    hex_col = _rgb_to_hex(c.get("rgb"))
                    if has_html_color and hex_col and not val.html_color:
                        val.write({'html_color': hex_col})
                color_vals_map[label] = val

                # Tallas que cuelgan de este color
                for s in (c.get("sizes") or []):
                    size_name = s.get("size")
                    if not size_name:
                        continue
                    if size_name not in size_vals_map:
                        sval = AttrVal.search([('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1)
                        if not sval:
                            sval = AttrVal.create({'name': size_name, 'attribute_id': size_attr.id})
                        size_vals_map[size_name] = sval

            attribute_lines = []
            if color_vals_map:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_vals_map.values()])]
                })
            if size_vals_map:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_vals_map.values()])]
                })

            tmpl_vals = {
                'name': full_name,
                'default_code': catalog_ref,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
            }

            try:
                tmpl = ProductTmpl.create(tmpl_vals)
                existing_refs.add(catalog_ref)
                created_any = True
                _logger.info(f"✅ Creado template {catalog_ref}")
            except Exception as e:
                _logger.error(f"❌ Error creando {catalog_ref}: {e}")
                continue

            # Imagen de portada del template (si existe)
            try:
                imgs = data.get("images") or []
                for img in imgs:
                    url = img.get("url_image")
                    if not url:
                        continue
                    bin_img = get_image_binary_from_url(url)
                    if bin_img:
                        tmpl.image_1920 = bin_img
                        break
            except Exception as e:
                _logger.warning(f"⚠️ No se pudo asignar imagen a template {catalog_ref}: {e}")

        if not created_any:
            _logger.info(f"✅ Página {page_number} sin nuevos productos.")
        icp.set_param('toptex_last_page', str(page_number + 1))
        _logger.info(f"OFFSET GUARDADO -> {page_number + 1}")

    # -------------------------------------------------
    # Stock (ya probado en tu entorno)
    # -------------------------------------------------
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return
        headers["x-toptex-authorization"] = token.strip()

        Product = self.env['product.product']
        Quant = self.env['stock.quant']
        Location = self.env['stock.location']

        internal_loc = Location.search([('usage', '=', 'internal')], limit=1)
        if not internal_loc:
            _logger.warning("❌ No hay ubicación interna para crear quants.")
            return

        for variant in Product.search([('default_code', '!=', False)]):
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
                warehouses = js.get("warehouses", []) if isinstance(js, dict) else (js[0].get("warehouses", []) if isinstance(js, list) and js else [])
                stock = 0
                for wh in warehouses:
                    if isinstance(wh, dict) and wh.get("id") == "toptex":
                        stock = int(wh.get("stock", 0))
                        break
            except Exception as e:
                _logger.error(f"❌ JSON inventario {sku}: {e}")
                stock = 0

            quant = Quant.search([('product_id', '=', variant.id), ('location_id', '=', internal_loc.id)], limit=1)
            if quant:
                quant.write({'quantity': stock, 'inventory_quantity': stock})
            else:
                Quant.create({'product_id': variant.id, 'location_id': internal_loc.id, 'quantity': stock, 'inventory_quantity': stock})
            _logger.info(f"✅ stock.quant actualizado para {sku}: {stock}")

    # -------------------------------------------------
    # Imágenes por variante (SIN llamar por SKU)
    # -------------------------------------------------
    def sync_variant_images_from_api(self):
        """
        Trae las fotos por color de la ficha del producto (catalog_reference)
        y las asigna a cada variante según su valor del atributo 'Color'.
        Además actualiza el swatch (html_color) del valor de Color si viene en la API.
        """
        icp = self.env['ir.config_parameter'].sudo()
        proxy   = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        user    = icp.get_param('toptex_username')
        pwd     = icp.get_param('toptex_password')

        # Auth
        auth_url = f"{proxy}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": user, "password": pwd},
                              headers=headers, timeout=20).json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return
        headers["x-toptex-authorization"] = token.strip()

        AttrVal = self.env['product.attribute.value']
        has_html_color = 'html_color' in AttrVal._fields

        for tmpl in self.search([('default_code', '!=', False)]):
            catalog_ref = tmpl.default_code
            url = f"{proxy}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code != 200:
                _logger.warning(f"❌ {catalog_ref}: {r.status_code} {r.text}")
                continue

            try:
                data = r.json()
                if isinstance(data, list) and data:
                    data = data[0]
                elif not isinstance(data, dict):
                    _logger.warning(f"❌ Sin datos para {catalog_ref}, saltando.")
                    continue
            except Exception:
                _logger.warning(f"❌ JSON inválido para {catalog_ref}, saltando.")
                continue

            # Mapa color->url y actualización de swatch
            color_imgs = {}
            for c in data.get("colors", []) or []:
                label = (c.get("colors", {}) or {}).get("es") or (c.get("colors", {}) or {}).get("en")
                if not label:
                    continue
                # Preferimos packshot FACE; fallback a cualquier imagen
                url_pic = (c.get("packshots", {}) or {}).get("FACE", {}) or {}
                url_pic = url_pic.get("url_packshot") or ""
                if not url_pic:
                    # Fallback extra (por si viniera otro nombre)
                    pics = (c.get("packshots", {}) or {})
                    for v in pics.values():
                        if isinstance(v, dict) and v.get("url_packshot"):
                            url_pic = v["url_packshot"]
                            break
                if url_pic:
                    color_imgs[label] = url_pic

                # Guardar color en el valor del atributo para swatch web
                if has_html_color:
                    hex_col = _rgb_to_hex(c.get("rgb"))
                    if hex_col:
                        val = AttrVal.search([('name', '=', label), ('attribute_id.name', '=', 'Color')], limit=1)
                        if val and not val.html_color:
                            try:
                                val.write({'html_color': hex_col})
                            except Exception:
                                pass

            # Asignar a cada variante según su Color
            for variant in tmpl.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                color = color_val.name if color_val else ""
                url_img = color_imgs.get(color)
                if not url_img:
                    continue
                bin_img = get_image_binary_from_url(url_img)
                if bin_img:
                    variant.image_1920 = bin_img
                    _logger.info(f"🖼️ Imagen asignada a {variant.default_code} ({color})")
                else:
                    _logger.warning(f"⚠️ No se pudo descargar imagen para {variant.default_code} ({color})")