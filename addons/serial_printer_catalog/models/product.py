# -*- coding: utf-8 -*-
import requests
from odoo import models, fields

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado de catálogo'
    _rec_name = 'name'

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Char(string="ID TopTex", required=True, index=True)
    reference = fields.Char(string="Referencia")
    description = fields.Text(string="Descripción")
    price = fields.Float(string="Precio")
    stock = fields.Integer(string="Stock")

    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for product in products:
                self.env['serial.printer.product'].create({
                    'name': product.get('name'),
                    'toptex_id': product.get('id'),
                    'reference': product.get('reference'),
                    'description': product.get('description'),
                    'price': product.get('price'),
                    'stock': product.get('stock', 0),
                })
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    def run_sync_cron(self):
        self.sync_products_from_api()