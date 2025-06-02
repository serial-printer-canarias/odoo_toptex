import requests
from odoo import models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_param('toptex_api_key')
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros en la configuración del sistema.")

        # Paso 1: Obtener token
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
            raise UserError("No se recibió token de autenticación.")

        # Paso 2: Llamada al producto NS300
        sku = "NS300.68558_68494"
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al recuperar el producto NS300: {response.text}")

        product_data = response.json()
        if not isinstance(product_data, dict):
            raise UserError("Respuesta inesperada de la API de TopTex (no es un dict).")

        # Paso 3: Crear el producto en Odoo
        name = product_data.get("name", "Producto sin nombre")
        default_code = product_data.get("sku", "NS300")  # SKU
        description = product_data.get("description", "")
        price = product_data.get("public_price", 0.0)

        existing_product = self.search([('default_code', '=', default_code)], limit=1)
        if existing_product:
            existing_product.write({
                'name': name,
                'list_price': price,
                'description': description,
            })
        else:
            self.create({
                'name': name,
                'default_code': default_code,
                'list_price': price,
                'description': description,
                'type': 'product',
            })