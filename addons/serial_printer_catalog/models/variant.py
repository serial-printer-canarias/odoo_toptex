from odoo import models, fields, api
import requests

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante de producto (talla/color)'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Integer(string="ID Variante TopTex")
    product_toptex_id = fields.Integer(string="ID Producto TopTex")
    size = fields.Char(string="Talla")
    color = fields.Char(string="Color")
    stock = fields.Integer(string="Stock")

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.env["serial.printer.variant"].sudo().update_or_create_variant(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_variant(self, item):
        existing = self.env["serial.printer.variant"].sudo().search([
            ("toptex_id", "=", item.get("id"))
        ], limit=1)

        values = {
            "name": item.get("name"),
            "toptex_id": item.get("id"),
            "product_toptex_id": item.get("productId"),
            "size": item.get("size"),
            "color": item.get("color"),
            "stock": item.get("stock", 0),
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)