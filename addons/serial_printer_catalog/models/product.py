import requests
from odoo import models, fields, api
from odoo.exceptions import UserError


class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Serial Printer Product'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID toptex")

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no configurado")
        return param

    def _generate_token(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token_url = 'https://api.toptex.io/v3/authenticate'

        headers = {
            'x-api-key': self._get_toptex_credential('toptex_api_key'),
            'Accept': 'application/json',
            'Accept-Encoding': 'identity',
        }

        data = {
            "username": self._get_toptex_credential('toptex_username'),
            "password": self._get_toptex_credential('toptex_password')
        }

        response = requests.post(
            proxy_url,
            params={'url': token_url},
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            return response.json().get('token')
        else:
            raise UserError(f"Error al generar token: {response.text}")

    @api.model
    def sync_products_from_api(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        catalog_url = 'https://api.toptex.com/v3/products/all?usage_right=b2b_uniquement&result_in_file=1'
        product_url = 'https://api.toptex.io/v3/products?usage_right=b2b_b2c&catalog_reference=ns300'
        token = self._generate_token()

        headers = {
            'x-api-key': self._get_toptex_credential('toptex_api_key'),
            'x-toptex-authorization': token,
            'Accept': 'application/json'
        }

        response = requests.get(
            proxy_url,
            params={'url': product_url},
            headers=headers,
        )

        if response.status_code == 200:
            catalog = response.json()
            for product_data in catalog.get('items', []):
                self._create_or_update_product(product_data)
        else:
            raise UserError(f"Error al obtener catálogo: {response.text}")

    def _create_or_update_product(self, product_data):
        toptex_id = product_data.get('id')
        name = product_data.get('label')

        product = self.search([('toptex_id', '=', toptex_id)], limit=1)
        if product:
            product.name = name
        else:
            self.create({'name': name, 'toptex_id': toptex_id})
