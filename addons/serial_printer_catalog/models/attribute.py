from odoo import models, fields, api
import requests

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto externo'

    name = fields.Char(string='Nombre del atributo', required=True)
    code = fields.Char(string='Código del atributo')

    @api.model
    def sync_attributes_from_api(self):
        url = "https://api.toptex.io/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for attr in data:
                self.create_or_update_attribute(attr)
        else:
            raise Exception("Error al obtener atributos de la API")

    def create_or_update_attribute(self, attr):
        existing = self.search([('code', '=', attr.get('code'))], limit=1)
        values = {
            'name': attr.get('name'),
            'code': attr.get('code'),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)