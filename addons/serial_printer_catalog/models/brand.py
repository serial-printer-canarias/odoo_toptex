from odoo import models, fields, api
import requests

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marca externa del catálogo'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.io/brands"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for brand in data:
                self.create_or_update_brand(brand)
        else:
            raise Exception("Fallo al conectar con la API de TopTex")

    def create_or_update_brand(self, brand):
        existing = self.search([('code', '=', brand.get('code'))], limit=1)
        values = {
            'name': brand.get('name'),
            'code': brand.get('code'),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)