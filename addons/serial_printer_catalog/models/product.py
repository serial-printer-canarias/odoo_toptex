import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # 1. Crear producto de prueba
        try:
            self.env['product.template'].create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'consu',
                'list_price': 9.99,
                'categ_id': self.env.ref('product.product_category_all').id
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")
            return

        # 2. Obtener parámetros
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales para autenticar con TopTex.")
            return

        # 3. Generar token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }
        headers = {'Content-Type': 'application/json'}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=headers)
            auth_response.raise_for_status()
            token_data = auth_response.json()
            access_token = token_data.get('accessToken')
            _logger.info(f"🟢 Token recibido: {access_token}")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # 4. Obtener producto real por SKU
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-toptex-authorization": access_token,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            _logger.info(f"🟢 JSON recibido desde TopTex.")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde la API: {e}")
            return

        # 5. Mapear y crear producto real
        try:
            # Asegura que data es un dict, no lista
            if isinstance(data, list):
                data = data[0]

            mapped = {
                'name': data.get('translatedName', {}).get('es') or data.get('designation', 'Sin nombre'),
                'default_code': data.get('sku', sku),
                'type': 'consu',
                'list_price': 19.99,
                'categ_id': self.env.ref('product.product_category_all').id,
            }
            self.env['product.template'].create(mapped)
            _logger.info("✅ Producto real creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto real desde JSON: {e}")