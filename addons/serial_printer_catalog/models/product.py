from odoo import models, fields, api
import requests

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado de catálogo'

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Integer(string="ID TopTex", required=True, index=True)
    reference = fields.Char(string="Referencia")
    description = fields.Text(string="Descripción")
    price = fields.Float(string="Precio")
    stock = fields.Integer(string="Stock")

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.env["serial.printer.product"].sudo().update_or_create_product(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_product(self, item):
        existing = self.env["serial.printer.product"].sudo().search([
            ("toptex_id", "=", item.get("id"))
        ], limit=1)

        values = {
            "name": item.get("name"),
            "toptex_id": item.get("id"),
            "reference": item.get("reference"),
            "description": item.get("description"),
            "price": item.get("price", 0),
            "stock": item.get("stock", 0),
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)

    @api.model
    def run_sync_cron(self):
        self.sync_products_from_api()