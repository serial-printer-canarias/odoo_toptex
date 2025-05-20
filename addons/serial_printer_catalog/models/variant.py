from odoo import models, fields, api
import requests

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variantes de productos'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    product_template_id = fields.Many2one('product.template', string='Producto')
    attribute_ids = fields.Many2many('product.attribute.value', string='Atributos')

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/products/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")

        data = response.json()

        for item in data:
            toptex_id = item.get('id')
            name = item.get('label')

            template_id = self.env['product.template'].search([
                ('default_code', '=', item.get('product'))
            ], limit=1)

            attribute_values = []
            for attr in item.get('attributes', []):
                val = self.env['product.attribute.value'].search([
                    ('name', '=', attr.get('value'))
                ], limit=1)
                if val:
                    attribute_values.append(val.id)

            variant = self.search([('toptex_id', '=', toptex_id)], limit=1)
            if variant:
                variant.write({
                    'name': name,
                    'product_template_id': template_id.id if template_id else False,
                    'attribute_ids': [(6, 0, attribute_values)],
                })
            else:
                self.create({
                    'name': name,
                    'toptex_id': toptex_id,
                    'product_template_id': template_id.id if template_id else False,
                    'attribute_ids': [(6, 0, attribute_values)],
                })