import requests
from odoo import models, fields, api

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributos del catálogo'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Integer(string='ID en TopTex', required=True, unique=True)
    type = fields.Selection([('size', 'Talla'), ('color', 'Color')], string='Tipo')

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
    def update_or_create_attribute(self, attr):
        attr_type = 'size' if attr.get('code') == 'size' else 'color'
        existing = self.search([('toptex_id', '=', attr.get('id'))], limit=1)
        values = {
            "name": attr.get("name"),
            "toptex_id": attr.get("id"),
            "type": attr_type
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)