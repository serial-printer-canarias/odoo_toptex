import requests
import logging
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_param('toptex_api_key')
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros de configuración (usuario, contraseña, API key o proxy_url).")

        # Paso 1: obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token de autenticación de TopTex.")

        # Paso 2: obtener un producto (NS300 por SKU)
        sku = "NS300_68558_68494"
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError("No se pudo recuperar el catálogo desde la API de TopTex.")

        data = response.json()

        _logger.warning("Respuesta JSON TopTex: %s", data)

        if not isinstance(data, list):
            raise UserError("Respuesta inesperada de la API de TopTex (no es una lista).")

        product_data = data[0] if data else None
        if not product_data:
            raise UserError("No se encontró ningún producto en la respuesta de TopTex.")

        # Paso 3: crear el producto en Odoo
        name = product_data.get("name", "Producto sin nombre")
        default_code = product_data.get("sku")
        description = product_data.get("description", "")

        self.env['product.template'].create({
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'description_sale': description,
        })

        _logger.info(f"Producto '{name}' creado correctamente desde la API de TopTex.")