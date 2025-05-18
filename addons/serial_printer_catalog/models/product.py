from odoo import models, fields
import requests

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def sync_stock_from_api(self):
        url = "https://api.toptex.com/api/products/stock"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for item in data:
                product = self.search([("default_code", "=", item["reference"])], limit=1)
                if product:
                    product.qty_available = item.get("stock", 0)