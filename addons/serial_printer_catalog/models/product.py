from odoo import models, fields, api
import requests

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    external_code = fields.Char(string='Código externo (TopTex)')

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for p in products:
                vals = {
                    'name': p.get('name', ''),
                    'default_code': p.get('reference'),
                    'external_code': p.get('code'),
                    'list_price': float(p.get('price', 0.0)),
                }
                existing = self.env['product.template'].search([('external_code', '=', p.get('code'))], limit=1)
                if existing:
                    existing.write(vals)
                else:
                    self.create(vals)
        else:
            raise Exception(f"Error al sincronizar productos: {response.status_code} - {response.text}")

    @api.model
    def sync_stock_from_api(self):
        url = "https://api.toptex.io/stock"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            stock_data = response.json()
            for item in stock_data:
                code = item.get('product_code')
                qty = item.get('stock', 0)
                product = self.env['product.template'].search([('external_code', '=', code)], limit=1)
                if product:
                    product.write({'qty_available': qty})
        else:
            raise Exception(f"Error al sincronizar stock: {response.status_code} - {response.text}")