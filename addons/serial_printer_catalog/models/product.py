import requests
from odoo import models, fields, api

class SerialPrinterProduct(models.Model):
    _name = "serial.printer.product"
    _description = "Producto del catálogo"

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Integer(string="ID en TopTex", required=True, unique=True)
    reference = fields.Char(string="Referencia")
    price = fields.Float(string="Precio base")
    stock = fields.Integer(string="Stock")
    image_url = fields.Char(string="URL de imagen")

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                self.env["serial.printer.product"].sudo().update_or_create_product(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def sync_images_from_api(self):
        url = "https://api.toptex.io/api/products/images"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("toptex_id", "=", item.get("product_id"))], limit=1)
                if product:
                    product.image_url = item.get("url")
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def sync_prices_from_api(self):
        url = "https://api.toptex.io/api/products/prices"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("toptex_id", "=", item.get("product_id"))], limit=1)
                if product:
                    product.price = item.get("price", 0.0)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_product(self, item):
        existing = self.search([("toptex_id", "=", item.get("id"))], limit=1)
        values = {
            "name": item.get("name"),
            "toptex_id": item.get("id"),
            "reference": item.get("reference"),
            "price": item.get("price", 0.0),
            "stock": item.get("stock", 0),
        }
        if existing:
            existing.write(values)
        else:
            self.create(values)