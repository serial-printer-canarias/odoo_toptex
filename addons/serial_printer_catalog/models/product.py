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
        token = "eyJraWQiOiJ3NXAxK0lqRjR5YVB3ME9nYnZsblJcL1N4RmhMaFVZZ2pHTlhUZlpUN0NURT0iLCJhbGciOiJSUzI1NiJ9.eyJjdXN0b206Y291bnRyeSI6IkVTIiwic3ViIjoiNDAxMjI1OTEtNzliZi00YzIxLWE2NjgtZmU0YmQ1YzhiMjliIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsImN1c3RvbTpuYXRpdmVfdmlwIjoiMCIsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS1jZW50cmFsLTEuYW1hem9uYXdzLmNvbVwvZXUtY2VudHJhbC0xX1YzQmtQcHBsYSIsImNvZ25pdG86dXNlcm5hbWUiOiJ0b2VzX2JhZmFsdXlkZWxyZXltYXJjIiwiY3VzdG9tOmNvbXBhbnkiOiJUT0VTIiwiYXVkIjoiMTRjdjJ2czIzdWs5OWo5aGxhOWlvdmttMTkiLCJldmVudF9pZCI6IjQyOTQyYzQ0LTVjMjgtNGY3Yy05NDk2LThkYzM4OTQ1MmI3YiIsInRva2VuX3VzZSI6ImlkIiwiY3VzdG9tOm5hdGl2ZV9wYXJ0bmVyIjoiMSIsImF1dGhfdGltZSI6MTc0ODA4OTg0MywiZXhwIjoxNzQ4MDkzNDQzLCJpYXQiOjE3NDgwODk4NDMsImVtYWlsIjoibWFyY2JhZmFsdXlAZ21haWwuY29tIiwiY3VzdG9tOm1hc3Rlcl91c2VybmFtZSI6InRvZXNfYmFmYWx1eWRlbHJleW1hcmMifQ.kOml0gi5ZBF-XGgpXLGptvIpu0OJPiA1boPDREegX3Iv3ygVtSaGDYTV8CFnuLWZHyW0_E-GXjo-f070LTk-F7S58NBivEhPZTofqcbwAD6EGAysoF9R19YrbuWmumzektb3aDMzfNsrYjWl6NUJSP_usNmEWLTXxIUyCzi7IHPaD-n_PUW1wXGFbardbU3rJmZfWLYY2Sx85BiFLhDraxL8r0Ye-PYOawPIV8-yc3gzswVgd9dUzhnE_F3OkN8QFdQxED0ZotnINgaTHSDHNdGgtdGau4x7HaaoRzb6nzI4qKxODHB6-2lDxDsaKFfWWAeb2JVPZ4UhnwrRoKNKwA"

        url = "https://api.toptex.io/v3/products"
        params = {
            "usage_right": "b2b_b2c",
            "lang": "es",
            "display_prices": "1"
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