from odoo import models, fields, api
import requests

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto desde API'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')

    @api.model
    def sync_attributes_from_api(self):
        url = "https://api.toptex.io/v1/products/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            attributes_data = response.json()
            for item in attributes_data:
                self.create_or_update_attribute(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_attribute(self, data):
        existing = self.search([('toptex_id', '=', str(data['id']))], limit=1)
        vals = {
            'name': data.get('name'),
            'toptex_id': str(data.get('id'))
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)