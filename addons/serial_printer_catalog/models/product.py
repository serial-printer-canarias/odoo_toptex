import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        _logger.info("🔄 Iniciando sincronización con la API de TopTex...")

        # Crear producto de prueba
        try:
            test_product = self.create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'consu',
                'list_price': 9.99,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
            _logger.info("✅ Producto de prueba creado correctamente: %s", test_product.name)
        except Exception as e:
            _logger.error("❌ Error al crear producto de prueba: %s", e)
            return

        # Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales o configuración en los parámetros del sistema.")
            return

        # Autenticación con la API
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

        # Llamada a la API de TopTex para obtener el producto NS300.68558_68494
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        product_headers = {
            'Content-Type': 'application/json',
            'x-toptex-authorization': access_token
        }

        try:
            product_response = requests.get(product_url, headers=product_headers)
            product_response.raise_for_status()
            product_json = product_response.json()
            _logger.info("🟢 JSON recibido desde TopTex: %s", product_json)
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto de la API: {e}")
            return

        # Mapper del JSON → Odoo
        try:
            name = product_json.get("translatedName", {}).get("es") or product_json.get("designation")
            default_code = product_json.get("reference") or sku
            list_price = 0.0
            product_vals = {
                'name': name,
                'default_code': default_code,
                'type': 'consu',
                'list_price': list_price,
                'categ_id': self.env.ref('product.product_category_all').id,
            }

            created = self.create(product_vals)
            _logger.info("✅ Producto real creado correctamente: %s", created.name)
        except Exception as e:
            _logger.error(f"❌ Error al crear producto real desde JSON: {e}")