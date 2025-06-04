import requests
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        _logger.info("🔄 Iniciando sincronización con la API de TopTex...")

        # 1. Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales o proxy en los parámetros del sistema.")
            return

        # 2. Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }

        try:
            response = requests.post(auth_url, json=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get('accessToken')
            _logger.info(f"🟢 Token recibido: {access_token}")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # 3. Crear producto de prueba
        try:
            product_test = self.env['product.template'].create({
                'name': 'Producto de Prueba',
                'default_code': 'TEST123',
                'type': 'product',
                'list_price': 9.99,
                'categ_id': 1,  # Asegúrate de que la categoría 1 existe
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")

        # 4. Obtener producto real desde TopTex
        sku = "