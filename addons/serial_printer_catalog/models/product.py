import json
import logging
import requests
import base64
import io
import time
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
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

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # --- Autenticación ---
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # --- DESCARGA LINK DEL CATALOGO COMPLETO ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        catalog_response = requests.get(catalog_url, headers=headers)
        if catalog_response.status_code != 200:
            raise UserError(f"❌ Error al obtener el link del catálogo: {catalog_response.status_code} - {catalog_response.text}")

        link_json = catalog_response.json()
        link = link_json.get('link')
        if not link:
            raise UserError("❌ No se recibió el link temporal para descargar el JSON del catálogo.")
        _logger.warning(f"🔗 Link temporal de descarga: {link}")

        # --- DESCARGA EL JSON DESDE LINK TEMPORAL ---
        products_json = []
        for intento in range(3):
            file_resp = requests.get(link, timeout=20)
            _logger.info(f"⏳ Intento {intento+1}: status={file_resp.status_code}")
            try:
                products_json = file_resp.json()
            except Exception as e:
                _logger.error(f"❌ Error al parsear JSON del catálogo: {e}")
                products_json = []
            if products_json:
                break
            time.sleep(1)

        _logger.warning(f"RESPUESTA CRUDA DEL JSON DE PRODUCTOS: {products_json}")

        if not products_json or not isinstance(products_json, list):
            raise UserError("❌ El catálogo descargado no es una lista de productos válida.")

        _logger.info(f"Procesando {len(products_json)} productos Toptex...")

        # Aquí empieza el mapeo, ejemplo SOLO para log. Aquí haces tu bucle, mapeo y creación igual que para NS300 pero con lista.
        for idx, product in enumerate(products_json):
            try:
                # Mapea datos principales, variantes, imágenes, stock, etc.
                # Este ejemplo SOLO loguea el nombre y código, debes mappear todo como en NS300 (usa tu código de variantes/atributos/stock)
                _logger.info(f"[{idx+1}/{len(products_json)}] Producto: {product.get('designation', {}).get('es', '')} | Ref: {product.get('catalogReference', '')}")
                # ... TODO: lógica de creación de productos igual que NS300 pero adaptado al array ...
            except Exception as e:
                _logger.error(f"❌ Error procesando producto {idx+1}: {e}")

        _logger.info("✅ Fin de la sincronización de catálogo Toptex.")