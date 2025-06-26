import requests
import base64
import logging
import io
from PIL import Image
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            _logger.info("✅ Imagen convertida a binario correctamente")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar la imagen: {e}")
    return None

def get_toptex_token(proxy_url, username, password):
    auth_url = f"{proxy_url}/v3/authenticate"
    response = requests.post(auth_url, json={"username": username, "password": password}, timeout=10)
    response.raise_for_status()
    return response.json()["token"]

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Aquí va tu código actual para crear/actualizar productos desde NS300.
        # No lo modifico por tu instrucción de no tocar lo que ya va bien.
        pass

    def sync_images_by_variant(self):
        """
        Sincroniza imágenes de variante por color usando TopTex API
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        if not all([api_key, proxy_url, username, password]):
            _logger.error("❌ Faltan credenciales para obtener imágenes por variante.")
            return

        # 1. Obtener token actualizado
        try:
            token = get_toptex_token(proxy_url, username, password)
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex para imágenes: {e}")
            return

        # 2. Obtener imágenes por variante (color)
        url = f"{proxy_url}/v3/products?catalog_reference={self.default_code}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                _logger.error(f"❌ Error obteniendo datos de producto para imágenes por variante: {response.status_code}")
                return
            data = response.json()
            colors = data.get("colors", [])
            for variant in self.product_variant_ids:
                # Busca el color de la variante Odoo
                color_val = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name.lower() == "color"
                )
                color_name = color_val.name if color_val else ""
                # Encuentra el color correspondiente en la respuesta TopTex
                color_data = next((c for c in colors if c.get("colors", {}).get("es") == color_name), None)
                if color_data:
                    packshots = color_data.get("packshots", {})
                    img_url = None
                    # Prioridad FACE, BACK, SIDE, ETC
                    for key in ["FACE", "BACK", "SIDE"]:
                        img = packshots.get(key, {})
                        if img.get("url_packshot"):
                            img_url = img["url_packshot"]
                            break
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"🖼️ Imagen asignada a variante {variant.name} desde {img_url}")
        except Exception as e:
            _logger.error(f"❌ Error asignando imágenes por variante: {e}")

    def sync_stock_from_api(self):
        """
        Sincroniza stock por variante usando TopTex API
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        if not all([api_key, proxy_url, username, password]):
            _logger.error("❌ Faltan credenciales para obtener stock por variante.")
            return

        # 1. Obtener token actualizado
        try:
            token = get_toptex_token(proxy_url, username, password)
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex para stock: {e}")
            return

        # 2. Obtener stock por variante
        url = f"{proxy_url}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                _logger.error(f"❌ Error obteniendo inventario por variante: {response.status_code}")
                return
            data = response.json()
            items = data.get("items", [])
            for variant in self.product_variant_ids:
                # Busca color/talla de la variante Odoo
                color_val = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name.lower() == "color"
                )
                size_val = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name.lower() == "size" or v.attribute_id.name.lower() == "talla"
                )
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""
                # Busca la entrada correspondiente por color/talla
                item = next(
                    (i for i in items if i.get("color") == color_name and i.get("size") == size_name),
                    None
                )
                if item:
                    stock = 0
                    warehouses = item.get("warehouses", [])
                    for wh in warehouses:
                        if wh.get("id") == "toptex":
                            stock = wh.get("stock", 0)
                            break
                    variant.qty_available = stock
                    _logger.info(f"📦 Stock actualizado para variante {variant.name}: {stock}")
        except Exception as e:
            _logger.error(f"❌ Error asignando stock por variante: {e}")