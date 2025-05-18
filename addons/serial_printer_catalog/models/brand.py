from odoo import models, fields, api
import requests

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Brand from TopTex'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.com/api/brands"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json().get("data", [])
            for brand in data:
                self.update_or_create_brand(brand)
        else:
            raise Exception(f"Error al obtener marcas de TopTex: {response.status_code}")

    def update_or_create_brand(self, brand):
        existing = self.search([('code', '=', brand.get('code'))], limit=1)
        values = {
            'name': brand.get('name'),
            'code': brand.get('code'),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)