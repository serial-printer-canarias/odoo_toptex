from odoo import models, fields, api
import requests

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante de producto externa'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    attribute_code = fields.Char(string='Código del atributo')
    attribute_id = fields.Many2one('serial.printer.attribute', string='Atributo relacionado')

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/attributes/values"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for var in data:
                attr_code = var.get('attribute_code')
                attr = self.env['serial.printer.attribute'].search([('code', '=', attr_code)], limit=1)
                values = {
                    'name': var.get('name'),
                    'code': var.get('code'),
                    'attribute_code': attr_code,
                    'attribute_id': attr.id if attr else False
                }
                existing = self.search([('code', '=', var.get('code'))], limit=1)
                if existing:
                    existing.write(values)
                else:
                    self.create(values)
        else:
            raise Exception("Error al obtener variantes desde la API")