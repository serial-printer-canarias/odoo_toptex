import requests
from odoo import models, fields, api
from datetime import datetime

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
        token = "eyJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3MTY0NzI2NjYsImV4cCI6MTcxNjQ3NzI2Nn0.oVg-nHt2ZHR3kK-6f1F1JqOqUvZkHUc0d0mD5b9dv6A"

        url = "https://api.toptex.io/v3/products"
        params = {
            "usage_right": "b2b_b2c",  # Obligatorio
            "lang": "es",              # Recomendado
            "display_prices": "1"      # Opcional, pero útil
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            products = response.json()
            for product in products:
                self.create_or_update_product(product)
        else:
            raise Exception(f"Error al conectar con la API: {response.status_code} - {response.text}")

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