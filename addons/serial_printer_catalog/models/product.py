import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------- UTILIDADES GENERALES ----------

def get_image_binary_from_url(url):
    """
    Descarga una imagen por URL y la convierte en binario para Odoo (base64).
    Siempre retorna None si hay error.
    """
    try:
        _logger.info(f"🖼️ Descargando imagen desde: {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            _logger.info(f"✅ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {str(e)}")
    return None

def get_credentials(env):
    """
    Lee las credenciales y parámetros del sistema Odoo.
    """
    icp = env['ir.config_parameter'].sudo()
    return {
        "username": icp.get_param('toptex_username'),
        "password": icp.get_param('toptex_password'),
        "api_key": icp.get_param('toptex_api_key'),
        "proxy_url": icp.get_param('toptex_proxy_url')
    }

def authenticate_toptex(creds):
    """
    Realiza autenticación en Toptex y devuelve el token válido o None.
    """
    auth_url = f"{creds['proxy_url']}/v3/authenticate"
    payload = {"username": creds['username'], "password": creds['password']}
    headers = {"x-api-key": creds['api_key'], "Content-Type": "application/json"}
    try:
        resp = requests.post(auth_url, json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            _logger.error(f"❌ Error autenticando: {resp.status_code} - {resp.text}")
            return None
        token = resp.json().get("token")
        if not token:
            _logger.error("❌ No se recibió un token válido.")
            return None
        _logger.info("🔐 Token recibido correctamente.")
        return token
    except Exception as e:
        _logger.error(f"❌ Excepción autenticando con TopTex: {e}")
        return None

def get_toptex_json(url, headers, what="petición"):
    """
    Wrapper seguro para peticiones GET a Toptex.
    """
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            _logger.error(f"❌ Error en {what}: {resp.status_code} - {resp.text}")
            return None
        return resp.json()
    except Exception as e:
        _logger.error(f"❌ Excepción en {what}: {e}")
        return None

def ensure_attribute(env, name):
    """
    Crea o devuelve el atributo de producto si no existe.
    """
    att = env['product.attribute'].search([('name', '=', name)], limit=1)
    if not att:
        att = env['product.attribute'].create({'name': name})
    return att

def ensure_attribute_value(env, attribute, value):
    """
    Crea o devuelve el valor de atributo si no existe.
    """
    val = env['product.attribute.value'].search([('name', '=', value), ('attribute_id', '=', attribute.id)], limit=1)
    if not val:
        val = env['product.attribute.value'].create({'name': value, 'attribute_id': attribute.id})
    return val

# ---------- MODELO PRINCIPAL ----------

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        """
        Sincroniza el producto NS300 completo (estructura, variantes, atributos, marca, imagen principal, precios).
        """
        creds = get_credentials(self.env)
        if not all(creds.values()):
            raise UserError("❌ Faltan credenciales o parámetros de sistema.")
        token = authenticate_toptex(creds)
        if not token:
            raise UserError("❌ No se pudo obtener token TopTex.")

        # --- Obtención de datos del catálogo principal NS300 ---
        catalog_url = f"{creds['proxy_url']}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {"x-api-key": creds['api_key'], "x-toptex-authorization": token}
        data = get_toptex_json(catalog_url, headers, what="catalogo NS300")
        if not data:
            raise UserError("❌ No se pudo obtener datos de TopTex.")

        if isinstance(data, list):  # Toptex a veces responde lista
            data = data[0] if data else {}

        # --- MARCA ---
        brand = data.get("brand", {}).get("name", {}).get("es", "") or ""
        # --- NOMBRE ---
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")

        # --- ATRIBUTOS Color y Talla ---
        color_attr = ensure_attribute(self.env, "Color")
        size_attr = ensure_attribute(self.env, "Talla")
        colors = data.get("colors", [])
        all_colors = set()
        all_sizes = set()
        for c in colors:
            color_name = c.get("colors", {}).get("es", "")
            all_colors.add(color_name)
            for sz in c.get("sizes", []):
                all_sizes.add(sz.get("size"))

        color_vals = {c: ensure_attribute_value(self.env, color_attr, c) for c in all_colors}
        size_vals = {s: ensure_attribute_value(self.env, size_attr, s) for s in all_sizes}

        attribute_lines = [
            {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
            {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]}
        ]

        # --- CREACIÓN de la plantilla ---
        template_vals = {
            'name': full_name,
            'default_code': data.get("catalogReference", "NS300"),
            'type': 'consu',  # solo consu + is_storable para stock
            'is_storable': True,
            'description_sale': description,
            'categ_id': self.env.ref("product.product_category_all").id,
            'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
        }
        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {template.name}")

        # --- IMAGEN PRINCIPAL de la plantilla ---
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    template.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                    break

        # --- PRECIOS por variante (llamada aparte) ---
        price_url = f"{creds['proxy_url']}/v3/products/price?catalog_reference=ns300"
        price_data = get_toptex_json(price_url, headers, what="precios")
        if price_data and "items" in price_data:
            items = price_data["items"]
            for variant in template.product_variant_ids:
                color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
                size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "talla").name
                coste = 0.0
                for it in items:
                    if it.get("color") == color and it.get("size") == size:
                        prices = it.get("prices", [])
                        if prices:
                            coste = float(prices[0].get("price", 0.0))
                        break
                variant.standard_price = coste
                variant.lst_price = coste * 1.25 if coste > 0 else 9.8
                _logger.info(f"💰 Variante: {variant.name} | Coste: {coste}")

        _logger.info(f"✅ Producto NS300 creado en Odoo y listo para ventas.")

    def sync_stock_from_api(self):
        """
        Actualiza el stock de cada variante usando la API de TopTex.
        """
        creds = get_credentials(self.env)
        if not all(creds.values()):
            _logger.error("❌ Faltan credenciales para stock.")
            return
        token = authenticate_toptex(creds)
        if not token:
            _logger.error("❌ Sin token válido para stock.")
            return
        inv_url = f"{creds['proxy_url']}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {"x-api-key": creds['api_key'], "x-toptex-authorization": token}
        inv_data = get_toptex_json(inv_url, headers, what="inventario")
        if not inv_data or "items" not in inv_data:
            _logger.error("❌ Sin datos de inventario Toptex.")
            return
        items = inv_data["items"]
        for variant in self.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "talla").name
            stock = 0
            for item in items:
                if item.get("color") == color and item.get("size") == size:
                    for wh in item.get("warehouses", []):
                        if wh.get("id") == "toptex":
                            stock = wh.get("stock", 0)
                            break
                    break
            variant.qty_available = stock
            _logger.info(f"🟩 Variante {variant.name} | Stock: {stock}")

    def sync_images_by_variant(self):
        """
        Asigna imágenes a cada variante usando los packshots de la API de TopTex.
        """
        creds = get_credentials(self.env)
        if not all(creds.values()):
            _logger.error("❌ Faltan credenciales para imágenes.")
            return
        token = authenticate_toptex(creds)
        if not token:
            _logger.error("❌ Sin token válido para imágenes.")
            return
        prod_url = f"{creds['proxy_url']}/v3/products?catalog_reference={self.default_code}&usage_right=b2b_b2c"
        headers = {"x-api-key": creds['api_key'], "x-toptex-authorization": token}
        prod_data = get_toptex_json(prod_url, headers, what="catalogo por variante")
        if not prod_data:
            _logger.error("❌ Sin datos de producto para imágenes de variante.")
            return
        if isinstance(prod_data, list):
            prod_data = prod_data[0] if prod_data else {}
        colors = prod_data.get("colors", [])
        for variant in self.product_variant_ids:
            color_name = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name.lower() == "color"
            ).name
            color_data = next((c for c in colors if c.get("colors", {}).get("es") == color_name), None)
            img_url = None
            if color_data:
                packshots = color_data.get("packshots", {})
                for key in ["FACE", "BACK", "SIDE"]:
                    img_info = packshots.get(key, {})
                    if img_info.get("url_packshot"):
                        img_url = img_info["url_packshot"]
                        break
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🟦 Imagen asignada a variante {variant.name}: {img_url}")