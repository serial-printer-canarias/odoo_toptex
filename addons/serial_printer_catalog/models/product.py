from odoo import models, fields, api
import requests

class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    external_id = fields.Char(string="ID Externo")
    synced_from_api = fields.Boolean(string="Sincronizado desde API", default=False)

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            products = response.json()
            for product in products:
                self.create_or_update_product(product)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_product(self, product_data):
        existing = self.search([('external_id', '=', product_data.get('id'))], limit=1)
        vals = {
            'name': product_data.get('name'),
            'external_id': product_data.get('id'),
            'default_code': product_data.get('sku'),
            'synced_from_api': True,
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)

    @api.model
    def sync_stock_from_api(self):
        url = "https://api.toptex.io/api/stock"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            stock_list = response.json()
            for item in stock_list:
                product = self.search([('external_id', '=', item.get('product_id'))], limit=1)
                if product:
                    product.write({
                        'qty_available': item.get('stock_quantity', 0)
                    })
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")