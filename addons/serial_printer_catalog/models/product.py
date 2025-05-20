from odoo import models, fields, api
import requests

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    external_code = fields.Char(string='Código externo TopTex')

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for prod in products:
                self.create_or_update_product(prod)
        else:
            raise Exception("No se pudo conectar con la API de productos")

    def create_or_update_product(self, prod):
        existing = self.search([('external_code', '=', prod.get('code'))], limit=1)
        values = {
            'name': prod.get('name'),
            'external_code': prod.get('code'),
            'default_code': prod.get('code'),
            'type': 'product',
            'list_price': prod.get('price', 0.0),
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)

    @api.model
    def sync_stock_from_api(self):
        url = "https://api.toptex.io/stocks"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            stock_data = response.json()
            for item in stock_data:
                product = self.search([('external_code', '=', item.get('code'))], limit=1)
                if product:
                    product.qty_available = item.get('quantity', 0.0)
        else:
            raise Exception("No se pudo conectar con la API de stock")