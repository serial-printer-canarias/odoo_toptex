import requests
from odoo import models, fields, api

class SerialPrinterVariant(models.Model):
    _name = "serial.printer.variant"
    _description = "Variante del producto (color/talla)"

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Integer(string="ID en TopTex", required=True, unique=True)
    product_id = fields.Many2one("serial.printer.product", string="Producto")
    color = fields.Char(string="Color")
    size = fields.Char(string="Talla")
    stock = fields.Integer(string="Stock disponible")

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/products/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            variants = response.json()
            for var in variants:
                self.env["serial.printer.variant"].sudo().update_or_create_variant(var)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_variant(self, var):
        product = self.env["serial.printer.product"].search([("toptex_id", "=", var.get("product_id"))], limit=1)
        if not product:
            return  # No creamos la variante si no existe el producto

        existing = self.search([("toptex_id", "=", var.get("id"))], limit=1)
        values = {
            "name": var.get("name"),
            "toptex_id": var.get("id"),
            "product_id": product.id,
            "color": var.get("color"),
            "size": var.get("size"),
            "stock": var.get("stock", 0),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)