import requests
from odoo import models, fields, api
from datetime import datetime
import pytz

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Productos desde la API TopTex'

    name = fields.Char(string="Nombre")
    reference = fields.Char(string="Referencia")
    toptex_id = fields.Char(string="TopTex ID")
    price = fields.Float(string="Precio")
    stock = fields.Integer(string="Stock")

    @api.model
    def sync_products_from_api(self):
        token = self.env['serial.printer.token'].get_valid_token()
        if not token:
            raise ValueError("Token de API no encontrado. Asegúrate de generar uno válido.")

        url = "https://api.toptex.io/v3/products"
        headers = {
            'Authorization': f'Bearer {token}',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE'
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.create_or_update_product(item)
        else:
            raise ValueError(f"Error en la llamada a la API: {response.status_code} - {response.text}")

    def create_or_update_product(self, item):
        product = self.search([('toptex_id', '=', item.get('id'))], limit=1)
        values = {
            'name': item.get('name'),
            'reference': item.get('reference'),
            'toptex_id': item.get('id'),
            'price': item.get('price', {}).get('sell', 0.0),
            'stock': item.get('stock', 0),
        }
        if product:
            product.write(values)
        else:
            self.create(values)