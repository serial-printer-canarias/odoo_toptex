from odoo import models, fields, api
import requests

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marca externa del catálogo'

    name = fields.Char(string="Nombre", required=True)
    external_id = fields.Char(string="ID Externo")

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
                self.create_or_update_brand(brand)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def create_or_update_brand(self, brand_data):
        existing = self.search([('external_id', '=', brand_data.get('id'))], limit=1)
        vals = {
            'name': brand_data.get('name'),
            'external_id': brand_data.get('id'),
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)