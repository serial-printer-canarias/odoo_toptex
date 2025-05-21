from odoo import models, api
import requests

class SerialPrinterPrices(models.Model):
    _inherit = 'serial.printer.product'

    @api.model
    def sync_prices_from_api(self):
        url = "https://api.toptex.io/api/products/prices"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            prices_data = response.json()
            for item in prices_data:
                product = self.env["serial.printer.product"].sudo().search([
                    ("toptex_id", "=", item.get("product_id"))
                ], limit=1)

                if product:
                    product.write({
                        "price": item.get("price", 0)
                    })
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")