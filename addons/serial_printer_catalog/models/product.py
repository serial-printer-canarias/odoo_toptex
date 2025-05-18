from odoo import models, api
import requests
import base64

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.com/api/products"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", [])
            for item in data:
                self.create_or_update_product(item)

    def create_or_update_product(self, item):
        default_code = item.get("reference")
        name = item.get("name", "")
        price = float(item.get("price", 0.0))
        product = self.search([("default_code", "=", default_code)], limit=1)

        values = {
            'name': name,
            'default_code': default_code,
            'list_price': price
        }

        if product:
            product.write(values)
        else:
            self.create(values)

    @api.model
    def sync_stock_from_api(self):
        url = "https://api.toptex.com/api/products/stock"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("default_code", "=", item.get("reference"))], limit=1)
                if product:
                    product.qty_available = item.get("stock", 0)

    @api.model
    def sync_images_from_api(self):
        url = "https://api.toptex.com/api/products/images"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("default_code", "=", item.get("reference"))], limit=1)
                if product and item.get("image_url"):
                    try:
                        img_data = requests.get(item["image_url"]).content
                        product.image_1920 = base64.b64encode(img_data)
                    except:
                        continue

    @api.model
    def sync_prices_from_api(self):
        url = "https://api.toptex.com/api/products/prices"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("default_code", "=", item.get("reference"))], limit=1)
                if product:
                    product.list_price = float(item.get("price", 0.0))