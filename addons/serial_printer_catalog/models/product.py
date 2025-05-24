import requests
from odoo import models, fields, api

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto Catálogo'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='TopTex ID')
    reference = fields.Char(string='Referencia')
    description = fields.Text(string='Descripción')
    brand = fields.Char(string='Marca')
    gender = fields.Char(string='Género')
    created_at = fields.Datetime(string='Fecha creación')
    updated_at = fields.Datetime(string='Fecha modificación')

    def sync_products_from_api(self):
        url = "https://api.toptex.io/v3/products"
        headers = {
            "Authorization": f"Bearer {self.env['serial.printer.token'].get_token()}",
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        params = {
            "usage_right": "b2b_b2c",
            "lang": "es",
            "display_prices": "1"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            products = response.json()
            for product in products:
                self.create_or_update_product(product)
        else:
            _logger.error(f"TopTex API error: {response.status_code} - {response.text}")

    def create_or_update_product(self, product_data):
        toptex_id = product_data.get("id")
        existing = self.search([('toptex_id', '=', toptex_id)], limit=1)

        values = {
            "name": product_data.get("name"),
            "toptex_id": toptex_id,
            "reference": product_data.get("reference"),
            "description": product_data.get("description"),
            "brand": product_data.get("brand"),
            "gender": product_data.get("gender"),
            "created_at": product_data.get("createdAt"),
            "updated_at": product_data.get("updatedAt"),
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)