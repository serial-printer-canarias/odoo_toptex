from odoo import models, api
import requests

class SerialPrinterImage(models.Model):
    _inherit = 'serial.printer.product'

    @api.model
    def sync_images_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for product in products:
                image_url = product.get("media", {}).get("imageUrl")
                if image_url:
                    self.env["serial.printer.product"].sudo()._update_product_image(product.get("id"), image_url)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def _update_product_image(self, toptex_id, image_url):
        product = self.env["serial.printer.product"].sudo().search([("toptex_id", "=", toptex_id)], limit=1)
        if product:
            image_content = requests.get(image_url).content
            product.image_1920 = image_content