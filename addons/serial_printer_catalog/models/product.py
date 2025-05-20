import requests
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_product_id = fields.Char(string='TopTex ID', readonly=True)
    toptex_brand = fields.Char(string='Marca', readonly=True)
    toptex_reference = fields.Char(string='Referencia', readonly=True)
    toptex_description = fields.Text(string='Descripción', readonly=True)

    @api.model
    def sync_products_from_api(self):
        url = 'https://api.toptex.io/api/products'
        headers = {
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE'
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for product in data.get('items', []):
                self.create_or_update_product(product)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def create_or_update_product(self, product_data):
        product = self.search([('toptex_product_id', '=', product_data.get('id'))], limit=1)
        values = {
            'name': product_data.get('label'),
            'toptex_product_id': product_data.get('id'),
            'toptex_brand': product_data.get('brand', {}).get('label'),
            'toptex_reference': product_data.get('reference'),
            'toptex_description': product_data.get('description', ''),
        }
        if product:
            product.write(values)
        else:
            self.create(values)

    @api.model
    def sync_stock_from_api(self):
        url = 'https://api.toptex.io/api/products/stock'
        headers = {
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE'
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for stock_item in data.get('items', []):
                product = self.search([('toptex_product_id', '=', stock_item.get('productId'))], limit=1)
                if product:
                    product.qty_available = stock_item.get('stock', 0)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")