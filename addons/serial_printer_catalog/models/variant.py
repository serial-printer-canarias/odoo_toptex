from odoo import models, fields, api
import requests

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante del producto'

    sku = fields.Char(string="SKU", required=True)
    product_id = fields.Many2one('product.template', string="Producto")
    color = fields.Char(string="Color")
    size = fields.Char(string="Talla")
    stock_quantity = fields.Integer(string="Stock")

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            variants = response.json()
            for variant in variants:
                self.create_or_update_variant(variant)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_variant(self, variant_data):
        existing = self.search([('sku', '=', variant_data.get('sku'))], limit=1)
        vals = {
            'sku': variant_data.get('sku'),
            'color': variant_data.get('color'),
            'size': variant_data.get('size'),
            'stock_quantity': variant_data.get('stock', 0),
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)