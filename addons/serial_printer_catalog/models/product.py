import requests
from odoo import models, api, _
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado de TopTex'

    @api.model
    def sync_products_from_api(self):
        # Parámetros de sistema
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        if not api_key or not username or not password:
            raise UserError("Faltan credenciales en los parámetros del sistema.")

        # URLs correctas
        auth_url = 'https://api.toptex.io/v3/authenticate'
        product_url = 'https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement'

        # Headers para token
        auth_headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }

        # Solicita el token
        auth_payload = {
            "username": username,
            "password": password
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error al generar token TopTex: {auth_response.text}")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("Token vacío o inválido")

        # Headers para productos
        product_headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }

        # Solicita el producto ns300
        response = requests.get(product_url, headers=product_headers)
        if response.status_code != 200:
            raise UserError(f"Error al obtener producto: {response.text}")

        result = response.json()
        if not isinstance(result, list) or not result:
            raise UserError("Respuesta inválida o vacía de TopTex")

        for product in result:
            name = product.get("label")
            reference = product.get("catalogReference")
            if name and reference:
                existing = self.env['product.template'].search([('default_code', '=', reference)])
                if not existing:
                    self.env['product.template'].create({
                        'name': name,
                        'default_code': reference,
                        'type': 'product',
                    })