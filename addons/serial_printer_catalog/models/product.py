from odoo import models, fields, api
import requests

class ProductTemplate(models.Model):
    _inherit = "product.template"

    toptex_id = fields.Char("TopTex ID")
    sync_date = fields.Datetime("Fecha de sincronización")

    def sync_stock_from_api(self):
        url = "https://api.toptex.com/v1/products"
        headers = {"Authorization": "Bearer TU_API_KEY"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            for item in response.json().get("products", []):
                product = self.env["product.template"].search([("toptex_id", "=", item["reference"])], limit=1)
                if product:
                    product.qty_available = item.get("stock", 0)