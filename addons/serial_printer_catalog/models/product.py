# serial_printer_catalog/models/product.py

from odoo import models, fields
import requests
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_code = fields.Char(string='Código TopTex')

    def sync_products_from_api(self):
        url = "https://api.toptex.io/v3/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4b0vgiZe"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            for product in data.get("items", []):
                existing_product = self.env['product.template'].search([
                    ('toptex_code', '=', product.get("code"))
                ], limit=1)

                vals = {
                    'name': product.get("name"),
                    'toptex_code': product.get("code"),
                    'type': 'product',
                    'sale_ok': True,
                    'purchase_ok': True,
                    'default_code': product.get("code")
                }

                if existing_product:
                    existing_product.write(vals)
                else:
                    self.env['product.template'].create(vals)

        except requests.exceptions.RequestException as e:
            _logger.error("Error al conectar con la API de TopTex: %s", str(e))