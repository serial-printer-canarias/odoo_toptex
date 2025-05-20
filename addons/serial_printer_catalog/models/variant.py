from odoo import models, fields, api
import requests

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante de producto desde API'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    product_template_id = fields.Many2one('product.template', string='Plantilla de producto')

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/v1/products/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.create_or_update_variant(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_variant(self, data):
        existing = self.search([('toptex_id', '=', str(data['id']))], limit=1)
        vals = {
            'name': data.get('name'),
            'toptex_id': str(data.get('id')),
            # Aquí podrías enlazar con el producto si tienes relación
            # 'product_template_id': ...
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)