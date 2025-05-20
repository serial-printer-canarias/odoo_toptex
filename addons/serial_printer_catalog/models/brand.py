import requests
from odoo import models, fields, api

class SerialPrinterBrand(models.Model):
    _name = "serial.printer.brand"
    _description = "Marcas del catálogo"

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Integer(string="ID en TopTex", required=True, unique=True)

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.io/api/brands"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.env["serial.printer.brand"].sudo().update_or_create_brand(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_brand(self, item):
        existing = self.env["serial.printer.brand"].sudo().search([
            ("toptex_id", "=", item.get("id"))
        ], limit=1)

        values = {
            "name": item.get("name"),
            "toptex_id": item.get("id")
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)