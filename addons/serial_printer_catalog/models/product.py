import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="ID TopTex")

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no configurado.")
        return param

    def _generate_token(self):
        url = "https://api.toptex.io/v3/authenticate"
        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        data = {
            "username": self._get_toptex_credential("toptex_username"),
            "password": self._get_toptex_credential("toptex_password"),
        }
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al generar token: {response.text}")
        return response.json().get("token")

    def sync_products_from_api(self):
        token = self._generate_token()
        url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al obtener producto TopTex: {response.text}")

        result = response.json()
        if not result or not isinstance(result, list):
            raise UserError("Respuesta inválida o vacía de TopTex")

        for product in result:
            name = product.get("label")
            reference = product.get("catalogReference")

            if not name or not reference:
                continue

            existing = self.env['product.template'].search([('default_code', '=', reference)], limit=1)
            if not existing:
                self.env['product.template'].create({
                    'name': name,
                    'default_code': reference,
                    'type': 'product',
                })