import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto de proveedor'
    _rec_name = 'name'

    toptex_id = fields.Char(string='TopTex ID', required=True, index=True)
    name = fields.Char(string='Nombre')
    description = fields.Text(string='Descripción')
    brand = fields.Char(string='Marca')
    category = fields.Char(string='Categoría')
    gender = fields.Char(string='Género')
    sizes = fields.Char(string='Tallas')
    colors = fields.Char(string='Colores')
    price = fields.Float(string='Precio base')
    currency = fields.Char(string='Moneda')

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
            "accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error {response.status_code}: {response.text}")

        data = response.json()
        for product in data:
            self.create_or_update_product(product)

    def create_or_update_product(self, product):
        vals = {
            'toptex_id': product.get('id'),
            'name': product.get('label'),
            'description': product.get('description'),
            'brand': product.get('brand', {}).get('label'),
            'category': product.get('category', {}).get('label'),
            'gender': product.get('gender'),
            'sizes': ', '.join(product.get('sizes', [])),
            'colors': ', '.join([color.get('label') for color in product.get('colors', [])]),
            'price': product.get('price', {}).get('unit_price', 0.0),
            'currency': product.get('price', {}).get('currency'),
        }

        existing = self.search([('toptex_id', '=', product.get('id'))], limit=1)
        if existing:
            existing.write(vals)
        else:
            self.create(vals)