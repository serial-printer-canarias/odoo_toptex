import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="TopTex ID")

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no está configurado")
        return param

    def sync_toptex_product(self):
        api_key = self._get_toptex_credential('toptex_api_key')
        username = self._get_toptex_credential('toptex_username')
        password = self._get_toptex_credential('toptex_password')

        auth_url = "https://api.toptex.io/v3/authenticate"
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }
        data = {
            "username": username,
            "password": password
        }

        token_response = requests.post(auth_url, json=data, headers=headers)
        if token_response.status_code != 200:
            raise UserError(f"Error al generar token TopTex: {token_response.text}")

        token = token_response.json().get("token")
        if not token:
            raise UserError("Token no recibido desde TopTex")

        product_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers["x-toptex-authorization"] = token

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al obtener datos de producto TopTex: {response.text}")

        result = response.json()
        if not result or not isinstance(result, list):
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
                        'toptex_id': str(product.get("id"))
                    })