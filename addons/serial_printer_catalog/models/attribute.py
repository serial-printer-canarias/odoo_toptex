from odoo import models, fields, api
import requests

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto (color, talla, etc.)'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Integer(string="ID TopTex", required=True, unique=True)

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
                self.env['serial.printer.attribute'].sudo().update_or_create_attribute(attr)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_attribute(self, data):
        existing = self.search([('toptex_id', '=', data.get('id'))], limit=1)
        values = {
            'name': data.get('name'),
            'toptex_id': data.get('id'),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)