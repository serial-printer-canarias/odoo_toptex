from odoo import models, fields, api
import requests

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto'

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código")

    @api.model
    def sync_attributes_from_api(self):
        url = "https://api.toptex.io/api/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            attributes = response.json()
            for attr in attributes:
                self.create_or_update_attribute(attr)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_attribute(self, attr_data):
        existing = self.search([('code', '=', attr_data.get('code'))], limit=1)
        vals = {
            'name': attr_data.get('name'),
            'code': attr_data.get('code'),
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)