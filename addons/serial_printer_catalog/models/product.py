import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductSync(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_product(self):
        # Parámetros del sistema
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        if not api_key or not username or not password:
            raise UserError("Faltan parámetros del sistema (API key, usuario o contraseña)")

        # Paso 1: Obtener el token
        token_url = 'https://api.toptex.io/v3/authenticate'
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        payload = {
            "username": username,
            "password": password,
        }

        response = requests.post(token_url, json=payload, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al generar token: {response.text}")
        token = response.json().get("token")

        # Paso 2: Llamar a producto específico (NS300)
        product_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers["x-toptex-authorization"] = token

        product_response = requests.get(product_url, headers=headers)
        if product_response.status_code != 200:
            raise UserError(f"Error al obtener producto: {product_response.text}")

        result = product_response.json()
        if not isinstance(result, list) or not result:
            raise UserError("Respuesta inválida o vacía de TopTex")

        # Paso 3: Crear producto si no existe
        for product in result:
            name = product.get("label")
            reference = product.get("catalogReference")
            if name and reference:
                existing = self.env['product.template'].search([('default_code', '=', reference)], limit=1)
                if not existing:
                    self.env['product.template'].create({
                        'name': name,
                        'default_code': reference,
                        'type': 'product',
                    })