import logging
import requests
import io
import base64
from PIL import Image
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

def get_token(api_key, proxy_url, username, password):
    """Autentica y devuelve el token JWT de Toptex."""
    auth_url = f"{proxy_url}/v3/authenticate"
    payload = {
        "username": username,
        "password": password,
    }
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    resp = requests.post(auth_url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data["token"]

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            _logger.info(f"✅ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido al descargar {url}")
    except Exception as e:
        _logger.warning(f"❌ Error procesando imagen de {url}: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def sync_images_by_variant(self):
        """
        Sincroniza imágenes por variante de color usando el JSON de Toptex.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        if not all([api_key, proxy_url, username, password]):
            _logger.error("❌ Faltan credenciales para imágenes por variante.")
            return

        token = get_token(api_key, proxy_url, username, password)
        product_url = f"{proxy_url}/v3/products?catalog_reference={self.default_code}&usage_right=b2b,b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }

        try:
            response = requests.get(product_url, headers=headers, timeout=15)
            if response.status_code != 200:
                _logger.error(f"❌ Error Toptex imágenes: {response.status_code}")
                return
            data = response.json()
            colors = data.get("colors", [])
            for variant in self.product_variant_ids:
                # Busca color_name en los atributos de la variante
                color_val = next(
                    (v for v in variant.product_template_attribute_value_ids if v.attribute_id.name.lower() == "color"),
                    None
                )
                color_name = color_val.name if color_val else ""
                color_data = next((c for c in colors if c.get("colors", {}).get("es") == color_name), None)
                if color_data:
                    packshots = color_data.get("packshots", {})
                    img_url = None
                    for key in ["FACE", "BACK", "SIDE"]:
                        img = packshots.get(key, {})
                        if img.get("url_packshot"):
                            img_url = img["url_packshot"]
                            break
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🟢 Imagen asignada a variante {variant.name} desde {img_url}")
        except Exception as e:
            _logger.error(f"Error asignando imágenes por variante: {e}")

    @api.model
    def sync_stock_from_api(self):
        """
        Actualiza el stock de cada variante usando el JSON de inventario de Toptex.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        if not all([api_key, proxy_url, username, password]):
            _logger.error("❌ Faltan credenciales para obtener stock por variante.")
            return

        token = get_token(api_key, proxy_url, username, password)
        inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }

        try:
            response = requests.get(inv_url, headers=headers, timeout=15)
            if response.status_code != 200:
                _logger.error(f"❌ Error Toptex stock: {response.status_code}")
                return
            data = response.json()
            items = data.get("items", [])
            for variant in self.product_variant_ids:
                color_val = next(
                    (v for v in variant.product_template_attribute_value_ids if v.attribute_id.name.lower() == "color"),
                    None
                )
                size_val = next(
                    (v for v in variant.product_template_attribute_value_ids if v.attribute_id.name.lower() == "size"),
                    None
                )
                color_code = color_val.name if color_val else ""
                size_code = size_val.name if size_val else ""
                # Busca stock por SKU/color/size
                stock_item = next(
                    (item for item in items
                     if item.get("color") == color_code and item.get("size") == size_code),
                    None
                )
                stock_qty = 0
                if stock_item:
                    # Suma stock de todos los almacenes
                    stock_qty = sum([w.get("stock", 0) for w in stock_item.get("warehouses", [])])
                variant.qty_available = stock_qty
                _logger.info(f"📦 Variante: {variant.name} | Stock: {stock_qty}")
        except Exception as e:
            _logger.error(f"Error actualizando stock de variantes: {e}")