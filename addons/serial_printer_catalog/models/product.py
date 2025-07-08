# -*- coding: utf-8 -*-
import logging
import requests
import base64
import io
from PIL import Image

from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 🔧 HERRAMIENTA GENÉRICA PARA DESCARGAR Y CONVERTIR IMÁGENES A BASE-64
# ---------------------------------------------------------------------------
def get_image_binary_from_url(url):
    """Devuelve la imagen en base64 (JPEG) o None."""
    try:
        _logger.info("🖼️  Descargando imagen: %s", url)
        resp = requests.get(url, stream=True, timeout=15)
        if resp.status_code == 200 and "image" in resp.headers.get("Content-Type", ""):
            img = Image.open(io.BytesIO(resp.content))
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue())
        _logger.warning("⚠️  No es imagen válida: %s", url)
    except Exception as e:
        _logger.warning("❌  Error imagen %s → %s", url, e)
    return None


# ---------------------------------------------------------------------------
# 🛒 MODELO PRODUCT.TEMPLATE – SINCRONIZACIÓN COMPLETA
# ---------------------------------------------------------------------------
class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ---------------------------------------------------
    # 1)  CREAR TODOS LOS PRODUCTOS (50 en 50)
    # ---------------------------------------------------
    @api.model
    def sync_products_from_api(self):
        """Crea / actualiza TODOS los productos del catálogo TopTex."""
        # --- Credenciales ---------------------------------------------------
        ICP = self.env["ir.config_parameter"].sudo()
        username = ICP.get_param("toptex_username")
        password = ICP.get_param("toptex_password")
        api_key  = ICP.get_param("toptex_api_key")
        proxy    = ICP.get_param("toptex_proxy_url")

        if not all([username, password, api_key, proxy]):
            raise UserError(_("❌  Faltan credenciales en Ajustes del Sistema."))

        # --- Autenticación ---------------------------------------------------
        token = self._ttx_authenticate(proxy, api_key, username, password)

        # --- Cabecera común --------------------------------------------------
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br",
        }

        # --- Atributos (Color, Talla) una sola vez ---------------------------
        attr_color = self._get_or_create_attribute("Color")
        attr_size  = self._get_or_create_attribute("Talla")

        # --- Bucle paginado (50/50) -----------------------------------------
        offset = 0
        page   = 1
        page_size = 50
        while True:
            url = (
                f"{proxy}/v3/products/all?"
                f"limit={page_size}&offset={offset}&usage_right=b2b_b2c"
            )
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code != 200:
                _logger.error("❌  Error página %s → %s", page, resp.text)
                break

            items = resp.json().get("items", [])
            if not items:
                break  # fin de catálogo

            _logger.info("📥  Página %s (%s artículos)", page, len(items))
            for data in items:
                self._create_or_update_from_json(
                    data, attr_color, attr_size, headers, proxy
                )

            # siguiente página
            offset += page_size
            page   += 1

        _logger.info("✅  Sincronización de productos COMPLETADA ✔")

    # ---------------------------------------------------
    # 2)  SERVER ACTION – STOCK
    # ---------------------------------------------------
    def sync_stock_from_api(self):
        ICP     = self.env["ir.config_parameter"].sudo()
        token   = self._ttx_authenticate(
            ICP.get_param("toptex_proxy_url"),
            ICP.get_param("toptex_api_key"),
            ICP.get_param("toptex_username"),
            ICP.get_param("toptex_password"),
        )
        proxy   = ICP.get_param("toptex_proxy_url")
        headers = {
            "x-api-key": ICP.get_param("toptex_api_key"),
            "x-toptex-authorization": token,
        }

        url = f"{proxy}/v3/products/inventory/all"
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise UserError(_("❌  Error stock → %s") % resp.text)

        StockQuant = self.env["stock.quant"]
        for item in resp.json().get("items", []):
            sku        = item.get("sku")
            total_qty  = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            variant    = self.env["product.product"].search(
                [("default_code", "=", sku)], limit=1
            )
            if not variant:
                continue
            quant = StockQuant.search(
                [("product_id", "=", variant.id),
                 ("location_id.usage", "=", "internal")], limit=1
            )
            if quant:
                quant.quantity = total_qty
                quant.inventory_quantity = total_qty
            _logger.info("📦  Stock %s → %s", sku, total_qty)

        _logger.info("✅  Stock actualizado ✔")

    # ---------------------------------------------------
    # 3)  SERVER ACTION – IMÁGENES POR VARIANTE
    # ---------------------------------------------------
    def sync_variant_images_from_api(self):
        ICP     = self.env["ir.config_parameter"].sudo()
        token   = self._ttx_authenticate(
            ICP.get_param("toptex_proxy_url"),
            ICP.get_param("toptex_api_key"),
            ICP.get_param("toptex_username"),
            ICP.get_param("toptex_password"),
        )
        proxy   = ICP.get_param("toptex_proxy_url")
        headers = {
            "x-api-key": ICP.get_param("toptex_api_key"),
            "x-toptex-authorization": token,
        }

        # --- Recorre TODAS las variantes del sistema ------------------------
        for variant in self.env["product.product"].search([("default_code", "!=", False)]):
            sku_parts = variant.default_code.split("_")
            if len(sku_parts) < 3:
                continue  # SKU no estándar
            catalog_ref = sku_parts[0]

            url = (
                f"{proxy}/v3/products?"
                f"catalog_reference={catalog_ref}&usage_right=b2b_b2c"
            )
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200 or not resp.json():
                continue
            data = resp.json()[0]

            color_es = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name.lower() == "color"
            ).name
            # Obtener packshot FACE de ese color
            img_url = ""
            for c in data.get("colors", []):
                if c.get("colors", {}).get("es") == color_es:
                    img_url = c.get("packshots", {}).get("FACE", {}).get("url_packshot")
                    break
            if img_url:
                img_b64 = get_image_binary_from_url(img_url)
                if img_b64:
                    variant.image_1920 = img_b64
                    _logger.info("🖼️  Imagen FACE actualizada → %s", variant.default_code)

        _logger.info("✅  Imágenes FACE por variante actualizadas ✔")

    # -----------------------------------------------------------------------
    #  UTILIDADES PRIVADAS
    # -----------------------------------------------------------------------
    def _ttx_authenticate(self, proxy, api_key, user, pwd):
        url = f"{proxy}/v3/authenticate"
        resp = requests.post(
            url,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={"username": user, "password": pwd},
            timeout=20,
        )
        if resp.status_code != 200:
            raise UserError(_("❌  Error autenticando → %s") % resp.text)
        token = resp.json().get("token")
        if not token:
            raise UserError(_("❌  Token vacío."))
        return token

    # -----------------------------
    def _get_or_create_attribute(self, name):
        attr = self.env["product.attribute"].search([("name", "=", name)], limit=1)
        return attr or self.env["product.attribute"].create({"name": name})

    # -----------------------------
    def _create_or_update_from_json(self, data, attr_color, attr_size, headers, proxy):
        """Crea o actualiza un product.template desde el JSON de TopTex."""
        default_code = data.get("catalogReference")
        if not default_code:
            return

        # --- Marca / Nombre / Descripción -------------
        brand  = (data.get("brand") or {}).get("name", {}).get("es", "") or "TopTex"
        name   = data.get("designation", {}).get("es", default_code)
        descr  = data.get("description", {}).get("es", "")
        title  = f"{brand} {name}".strip()

        template = self.search([("default_code", "=", default_code)], limit=1)
        if not template:
            template = self.create({
                "name": title,
                "default_code": default_code,
                "type": "consu",
                "is_storable": True,
                "description_sale": descr,
                "categ_id": self.env.ref("product.product_category_all").id,
            })
        else:
            template.write({"name": title, "description_sale": descr})

        # --- Atributos (Color / Talla) ----------------
        color_vals = {}
        size_vals  = {}
        for color in data.get("colors", []):
            col_name = color.get("colors", {}).get("es")
            if not col_name:
                continue
            color_vals.setdefault(col_name, self.env[
                "product.attribute.value"]._get_or_create(val_name=col_name,
                                                          attr=attr_color))
            for sz in color.get("sizes", []):
                size_name = sz.get("size")
                if not size_name:
                    continue
                size_vals.setdefault(size_name, self.env[
                    "product.attribute.value"]._get_or_create(val_name=size_name,
                                                              attr=attr_size))

        # Asignar líneas de atributo si no existen
        for attr, mapping in ((attr_color, color_vals), (attr_size, size_vals)):
            if not template.attribute_line_ids.filtered(lambda l: l.attribute_id == attr):
                template.attribute_line_ids = [(0, 0, {
                    "attribute_id": attr.id,
                    "value_ids": [(6, 0, [v.id for v in mapping.values()])],
                })]

        # --- Imagen principal -------------------------
        if not template.image_1920 and data.get("images"):
            img_b64 = get_image_binary_from_url(data["images"][0].get("url_image"))
            if img_b64:
                template.image_1920 = img_b64

        # --- PRECIOS + SKU ----------------------------
        self._update_variants_price_sku(template, data, proxy, headers)

    # -----------------------------
    def _update_variants_price_sku(self, template, data, proxy, headers):
        # 1) Inventario + 2) Precio para ese catalogReference
        catalog_ref = data.get("catalogReference")
        if not catalog_ref:
            return
        inv_url   = f"{proxy}/v3/products/inventory?catalog_reference={catalog_ref}"
        price_url = f"{proxy}/v3/products/price?catalog_reference={catalog_ref}"

        inv_data   = requests.get(inv_url, headers=headers, timeout=30).json().get("items", [])
        price_data = requests.get(price_url, headers=headers, timeout=30).json().get("items", [])

        def _sku(c, s):
            for i in inv_data:
                if i.get("color") == c and i.get("size") == s:
                    return i.get("sku")
            return ""

        def _cost(c, s):
            for p in price_data:
                if p.get("color") == c and p.get("size") == s and p.get("prices"):
                    return float(p["prices"][0].get("price", 0.0))
            return 0.0

        for var in template.product_variant_ids:
            color = var.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name.lower() == "color").name
            size  = var.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name.lower() == "talla").name
            var.default_code = _sku(color, size) or var.default_code
            cost = _cost(color, size)
            if cost:
                var.standard_price = cost
                var.lst_price      = round(cost * 1.25, 2)