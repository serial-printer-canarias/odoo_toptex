import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Paso 1: Crear producto de prueba
        try:
            test_product = self.create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'consu',
                'list_price': 9.99,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")
            return

        # Paso 2: Obtener parámetros
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales o proxy en parámetros del sistema.")
            return

        # Paso 3: Autenticación con la API (proxy)
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
            _logger.info(f"🟢 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Paso 4: Obtener producto desde API
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            'Content-Type': 'application/json',
            'x-toptex-authorization': access_token
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            product_data = response.json()
            _logger.info(f"📦 JSON recibido: {product_data}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener el producto de la API: {e}")
            return

        # Paso 5: Crear producto real con datos mínimos del JSON
        try:
            name = product_data.get("translatedName", {}).get("es") or "Sin nombre"
            default_code = product_data.get("reference") or sku

            self.create({
                'name': name,
                'default_code': default_code,
                'type': 'consu',
                'list_price': 12.34,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
            _logger.info(f"✅ Producto {default_code} creado desde API correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear el producto real desde API: {e}")