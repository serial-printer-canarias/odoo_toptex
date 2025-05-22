# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado de catálogo'

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Char(string="ID TopTex", required=True, index=True)
    ref = fields.Char(string="Referencia")
    description = fields.Text(string="Descripción")
    price = fields.Float(string="Precio")
    stock = fields.Integer(string="Stock")

    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        }

        _logger.warning(">>>> Llamando a API TopTex con headers: %s", headers)

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")

        data = response.json()

        for item in data.get("items", []):
            product_id = item.get("id")
            name = item.get("name", "")
            ref = item.get("reference", "")
            description = item.get("description", "")
            price = item.get("price", {}).get("net", 0.0)
            stock = item.get("stock", {}).get("total", 0)

            existing_product = self.search([('toptex_id', '=', product_id)], limit=1)

            if existing_product:
                existing_product.write({
                    'name': name,
                    'ref': ref,
                    'description': description,
                    'price': price,
                    'stock': stock,
                })
            else:
                self.create({
                    'toptex_id': product_id,
                    'name': name,
                    'ref': ref,
                    'description': description,
                    'price': price,
                    'stock': stock,
                })

    def run_sync_cron(self):
        self.sync_products_from_api()