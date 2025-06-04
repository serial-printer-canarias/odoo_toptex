import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_and_create_test(self):
        # 1. Crear producto de prueba
        try:
            test_product = self.create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'product',
                'list_price': 9.99,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")
            return

        # 2. Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales en los parámetros del sistema.")
            return

        # 3. Obtener token desde el proxy
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

        # 4. Obtener datos del producto real por SKU
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers['toptex-authorization'] = access_token

        try:
            product_response = requests.get(product_url, headers=headers)
            product_response.raise_for_status()
            product_data = product_response.json()
            _logger.info(f"📦 JSON recibido: {product_data}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener datos del producto desde TopTex: {e}")
            return

        # 5. Mapper para convertir JSON en campos de Odoo
        try:
            if not isinstance(product_data, dict):
                _logger.error("❌ La respuesta no es un objeto JSON válido (dict).")
                return

            name = product_data.get('translatedName', {}).get('es', 'Producto sin nombre')
            default_code = product_data.get('sku', 'SIN-CODIGO')
            price = product_data.get('publicPrice', 0.0)

            mapped_data = {
                'name': name,
                'default_code': default_code,
                'type': 'product',
                'list_price': price,
                'categ_id': self.env.ref('product.product_category_all').id,
            }

            self.create(mapped_data)
            _logger.info(f"✅ Producto real creado: {default_code} - {name}")
        except Exception as e:
            _logger.error(f"❌ Error al mapear o crear el producto real: {e}")