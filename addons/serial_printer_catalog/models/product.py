import requests
import os
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="TopTex ID", copy=False)

    def _get_toptex_proxy_headers(self):
        return {
            "x-api-key": os.getenv("toptex_api_key"),
            "x-toptex-username": os.getenv("toptex_username"),
            "x-toptex-password": os.getenv("toptex_password"),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }

    def _generate_token(self):
        proxy_url = os.getenv("toptex_proxy_url")
        auth_url = "https://api.toptex.com/v2/authentication/token"
        headers = self._get_toptex_proxy_headers()

        response = requests.post(proxy_url, params={"url": auth_url}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("token")
        else:
            _logger.error("Error al generar el token: %s", response.text)
            return None

    def sync_products_from_api(self):
        proxy_url = os.getenv("toptex_proxy_url")
        token = self._generate_token()
        if not token:
            _logger.error("Token vacío, no se puede continuar.")
            return

        catalog_url = "https://api.toptex.com/v3/products?usage_right=b2b_uniquement&result_in_file=1"
        headers = {
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }

        response = requests.get(proxy_url, params={"url": catalog_url}, headers=headers)
        if response.status_code != 200:
            _logger.error("Error al obtener productos: %s", response.text)
            return

        products = response.json()
        for product in products:
            if not product.get("sku") or not product.get("catalog_reference"):
                continue

            existing_product = self.env['product.template'].search([('toptex_id', '=', product["sku"])], limit=1)
            values = {
                "name": product["catalog_reference"],
                "toptex_id": product["sku"],
            }

            if existing_product:
                existing_product.write(values)
            else:
                self.env['product.template'].create(values)