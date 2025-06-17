import requests
import json
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # URL de autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("🟢 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # URL de producto
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"🟢 URL de producto: {product_url}")
            _logger.info(f"🟢 Headers de producto: {headers}")
            _logger.info(f"🟢 Respuesta cruda: {response.text}")

            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")

            data = response.json()

            # Validamos si es lista o dict
            if isinstance(data, list):
                data = data[0] if data else {}

            if not data:
                _logger.error("❌ No se encontraron datos dentro del dict")
                return

            _logger.info(f"🟢 JSON interpretado:\n{json.dumps(data, indent=2)}")

            # 🔧 🔧 Aquí después añadiremos el mapeo definitivo completo
            # De momento dejamos solo el logger puro para validar parsing

        except Exception as e:
            _logger.error(f"❌ Excepción general: {e}")