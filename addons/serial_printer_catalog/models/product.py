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
                'categ_id': self.env.ref('product.product_category_all').id
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")
            return

        # Paso 2: Leer parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales o parámetros del sistema.")
            return

        # Paso 3: Generar token desde la API
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"Error autenticando en TopTex: {auth_response.text}")
            token_data = auth_response.json()
            token = token_data.get("token")
            if not token:
                raise UserError("No se recibió un token válido de TopTex.")
            _logger.info(f"🟢 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Paso 4: Obtener producto desde la API
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"Error al obtener el producto: {response.text}")
            data = response.json()
            _logger.info(f"🟢 JSON recibido desde TopTex:\n{data}")
        except Exception as e:
            _logger.error(f"❌ Error al descargar o interpretar JSON: {e}")
            return

        # ✅ Protección para evitar "list index out of range"
        if isinstance(data, list):
            if len(data) == 0:
                _logger.error("❌ La lista de datos está vacía. No se puede crear el producto.")
                return
            data = data[0]

        # Paso 5: Mapear y crear producto real
        try:
            mapped = {
                'name': data['translatedName']['es'],
                'default_code': data['sku'],
                'type': 'consu',
                'list_price': 0.0,
                'categ_id': self.env.ref('product.product_category_all').id
            }
            self.create(mapped)
            _logger.info("✅ Producto real creado correctamente desde la API.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto real desde JSON: {e}")