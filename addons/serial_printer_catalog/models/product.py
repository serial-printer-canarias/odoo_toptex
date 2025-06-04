import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_and_create_test(self):
        # Crear producto de prueba
        try:
            test_product = self.create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'product',
                'list_price': 9.99,
                'categ_id': self.env.ref('product.product_category_all').id,
            })
            _logger.info("✅ Producto de prueba creado: %s", test_product.name)
        except Exception as e:
            _logger.error("❌ Error al crear producto de prueba: %s", str(e))

        # Parámetros de sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan parámetros en el sistema.")
            return

        # Autenticación
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_data = {
            'username': username,
            'password': password,
            'apiKey': api_key,
        }
        try:
            auth_response = requests.post(auth_url, json=auth_data)
            _logger.info("🔐 Auth status: %s", auth_response.status_code)
            if auth_response.status_code != 200:
                _logger.error("❌ Error autenticando: %s", auth_response.text)
                return
            token = auth_response.json().get('token')
        except Exception as e:
            _logger.error("❌ Error al autenticar: %s", str(e))
            return

        if not token:
            _logger.error("❌ Token vacío.")
            return

        # Petición de producto real
        sku = 'NS300.68558_68494'
        product_url = f'{proxy_url}/v3/products/{sku}?usage_right=b2b_uniquement'
        headers = {
            'toptex-authorization': token,
            'Content-Type': 'application/json'
        }
        try:
            response = requests.get(product_url, headers=headers)
            _logger.info("📦 Status producto: %s", response.status_code)
            _logger.debug("📦 JSON recibido: %s", response.text)
            if response.status_code != 200:
                _logger.error("❌ Error al obtener producto: %s", response.text)
                return
            product_json = response.json()
            if not isinstance(product_json, dict):
                _logger.warning("⚠️ Respuesta inesperada: %s", product_json)
                return
        except Exception as e:
            _logger.error("❌ Error al obtener producto: %s", str(e))
            return

        # Mapper de TopTex → Odoo
        try:
            name = product_json.get('translatedName', {}).get('es') or product_json.get('designation', 'Sin nombre')
            default_code = product_json.get('sku', sku)
            list_price = float(product_json.get('price', {}).get('public', 0.0))
            product_vals = {
                'name': name,
                'default_code': default_code,
                'type': 'product',
                'list_price': list_price,
                'categ_id': self.env.ref('product.product_category_all').id,
            }
            created = self.create(product_vals)
            _logger.info("✅ Producto API creado: %s", created.name)
        except Exception as e:
            _logger.error("❌ Error al mapear/crear producto API: %s", str(e))