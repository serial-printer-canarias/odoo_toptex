from odoo import models, fields, api
import requests

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marcas desde API'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Integer(string='ID TopTex', required=True, index=True, unique=True)

    @api.model
    def import_brands_from_api(self):
        url = "https://api.toptex.com/rest/catalog/brand"
        headers = {
            "X-AUTH-TOKEN": "TU_TOKEN_API_REAL",
            "X-AUTH-LOGIN": "TU_LOGIN_API_REAL"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            brands = response.json()
            for brand in brands:
                self.create_or_update_brand(brand)
        else:
            raise Exception(f"Error al obtener marcas: {response.status_code}")

    def create_or_update_brand(self, brand_data):
        existing = self.search([('toptex_id', '=', brand_data['id'])], limit=1)
        if existing:
            existing.name = brand_data['label']
        else:
            self.create({
                'name': brand_data['label'],
                'toptex_id': brand_data['id'],
            })