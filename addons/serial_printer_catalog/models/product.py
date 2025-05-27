from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import base64


class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto del catálogo'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID TopTex")
    reference = fields.Char(string="Referencia")
    description = fields.Text(string="Descripción")
    image = fields.Binary(string="Imagen")

    def _generate_token(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key') or ''
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username') or ''
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password') or ''

        url = 'https://api.toptex.io/v3/authenticate'
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
        }
        data = {
            'username': username,
            'password': password,
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            raise UserError(f"Error al generar token: {response.status_code} - {response.text}")

    @api.model
    def sync_products_from_api(self):
        token = self._generate_token()
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key') or ''

        url = 'https://api.toptex.io/v3/products?usage_right=b2b_b2c'
        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token,
            'Accept': 'application/json',
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            catalog = response.json()
            for product_data in catalog.get('items', []):
                self.create_or_update_product(product_data)
        else:
            raise UserError(f"Error al obtener catálogo: {response.status_code} - {response.text}")

    def create_or_update_product(self, product_data):
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
            'reference': product_data.get('reference', ''),
            'description': product_data.get('description', ''),
            'image': image_binary,
        }

        if product:
            product.write(values)
        else:
            self.create(values)