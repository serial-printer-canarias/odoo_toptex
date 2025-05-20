import requests
from odoo import models, fields, api

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Brand'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.io/api/brands"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for brand in data.get("hydra:member", []):
                    self.create_or_update_brand(brand)
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"API connection failed: {str(e)}")

    def create_or_update_brand(self, brand_data):
        self.env['serial.printer.brand'].sudo().update_or_create_brand(brand_data)

    @api.model
    def update_or_create_brand(self, brand_data):
        existing = self.search([('code', '=', brand_data.get("code"))], limit=1)
        values = {
            'name': brand_data.get("name"),
            'code': brand_data.get("code"),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)