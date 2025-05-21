from odoo import models, api, fields
import requests

class SerialPrinterPrice(models.Model):
    _inherit = 'serial.printer.product'

    customer_price = fields.Float(string="Precio personalizado", digits="Product Price")

    @api.model
    def sync_prices_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.env["serial.printer.product"].sudo().search([("toptex_id", "=", item.get("id"))], limit=1)
                if product:
                    # Supongamos que el precio base es item["price"]
                    base_price = item.get("price", 0.0)
                    customer_price = base_price * 1.25  # margen del 25%
                    product.customer_price = customer_price
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")