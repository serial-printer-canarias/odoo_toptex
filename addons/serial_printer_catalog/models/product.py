import requests
import logging
from odoo import models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Obtener parámetros del sistema
        IrConfig = self.env['ir.config_parameter'].sudo()
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')
        proxy_url = IrConfig.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            raise UserError("Faltan parámetros de configuración de la API de TopTex.")

        # Autenticación y obtención del token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }
        auth_headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error al autenticar con TopTex: {auth_response.text}")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("Token no recibido en la autenticación.")

        # SKU correcto
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products/{sku}?usage_right=b2b_uniquement"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept-Encoding": "gzip"
        }

        response = requests.get(product_url, headers=headers)
        _logger.info(f"URL llamada: {product_url}")
        _logger.info(f"Status code: {response.status_code}")
        _logger.info(f"Contenido recibido: {response.text}")

        if response.status_code != 200:
            raise UserError(f"Error al obtener producto desde TopTex: {response.text}")

        try:
            product_data = response.json()
        except Exception as e:
            raise UserError(f"No se pudo interpretar la respuesta JSON: {e}")

        if not isinstance(product_data, dict):
            raise UserError("La respuesta de la API no contiene un producto válido.")

        # Procesar datos para Odoo
        name = product_data.get('translatedName', {}).get('es') or product_data.get('name') or "Producto sin nombre"
        default_code = product_data.get('sku') or sku
        list_price = product_data.get('price', {}).get('public') or 0.0

        # Verificar si ya existe
        existing = self.search([('default_code', '=', default_code)], limit=1)
        if existing:
            _logger.info(f"Producto con SKU {default_code} ya existe.")
            return

        # Crear producto
        self.create({
            'name': name,
            'default_code': default_code,
            'list_price': list_price,
            'type': 'product',
        })
        _logger.info(f"Producto {name} creado correctamente.")