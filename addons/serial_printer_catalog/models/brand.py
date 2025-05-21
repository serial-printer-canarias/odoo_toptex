from odoo import models, fields, api
import requests

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marca de catálogo'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Integer(string="ID TopTex", required=True, unique=True)

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.io/api/brands"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            brands = response.json()
            for brand in brands:
                self.env['serial.printer.brand'].sudo().update_or_create_brand(brand)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_brand(self, data):
        existing = self.search([('toptex_id', '=', data.get('id'))], limit=1)
        values = {
            'name': data.get('name'),
            'toptex_id': data.get('id'),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)