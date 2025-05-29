import requests
import base64
import os

from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial_printer_product'
    _description = 'Producto del catálogo'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    reference = fields.Char(string='Referencia')
    description = fields.Text(string='Descripción')
    image = fields.Binary(string='Imagen')

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f'Falta el parámetro de configuración: {key}')
        return param

    def _generate_token(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        auth_url = "https://api.toptex.io/v3/authenticate"
        headers = {
            "x-api-key": self._get_toptex_credential('toptex_api_key'),
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        }
        data = {
            "username": self._get_toptex_credential('toptex_username'),
            "password": self._get_toptex_credential('toptex_password'),
        }
        response = requests.post(
            proxy_url,
            params={"url": auth_url},
            headers=headers,
            json=data
        )
        if response.status_code == 200:
            return response.json().get('token')
        else:
            raise UserError(f'Error al generar token ({response.status_code}): {response.text}')

    @api.model
    def sync_products_from_api(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token = self._generate_token()

        url = "https://api.toptex.com/v3/products/all?usage_right=b2b_uniquement&result_in_file=1"
        headers = {
            "x-api-key": self._get_toptex_credential('toptex_api_key'),
            "x-toptex-authorization": token,
            "Accept-Encoding": "identity",
            "Accept": "application/json"
        }

        response = requests.get(proxy_url, params={"url": url}, headers=headers)
        if response.status_code == 200:
            catalog = response.json().get('items', [])
            for product_data in catalog:
                self._create_or_update_product(product_data)
        else:
            raise UserError(f'Error al obtener catálogo ({response.status_code}): {response.text}')

    def _create_or_update_product(self, product_data):
        toptex_id = product_data.get('id')
        product = self.search([('toptex_id', '=', toptex_id)], limit=1)

        image_binary = False
        image_url = product_data.get('main_picture_url')
        if image_url:
            try:
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    image_binary = base64.b64encode(img_response.content)
            except Exception:
                pass

        values = {
            'name': product_data.get('name', ''),
            'toptex_id': toptex_id,
            'reference': product_data.get('reference'),
            'description': product_data.get('description', ''),
            'image': image_binary,
        }

        if product:
            product.write(values)
        else:
            self.create(values)