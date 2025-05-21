from odoo import models, fields, api

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante de producto'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Integer(string="ID TopTex", required=True, unique=True)
    product_template_id = fields.Many2one('serial.printer.product', string="Producto")
    attribute_ids = fields.Many2many('serial.printer.attribute', string="Atributos")

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")
        data = response.json()

        for item in data:
            variant = self.search([('toptex_id', '=', item.get('id'))], limit=1)
            values = {
                'name': item.get('name'),
                'toptex_id': item.get('id'),
            }
            if variant:
                variant.write(values)
            else:
                self.create(values)