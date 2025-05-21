# models/prices.py

import requests
from odoo import models, fields, api

class SerialPrinterPrices(models.Model):
    _name = 'serial.printer.price'
    _description = 'Precios personalizados desde TopTex'

    product_sku = fields.Char(string='SKU del Producto', required=True)
    customer_code = fields.Char(string='Código de Cliente')
    base_price = fields.Float(string='Precio base')
    discounted_price = fields.Float(string='Precio con descuento')

    @api.model
    def sync_prices_from_api(self):
        url = 'https://api.toptex.io/api/prices'
        headers = {
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE',
            'Accept': 'application/json',
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Error {response.status_code}: {response.text}")
            data = response.json()

            for item in data.get('prices', []):
                self.env['serial.printer.price'].create({
                    'product_sku': item.get('sku'),
                    'customer_code': item.get('customer_code'),
                    'base_price': item.get('base_price'),
                    'discounted_price': item.get('discounted_price'),
                })

        except Exception as e:
            raise Exception(f"Error al sincronizar precios: {str(e)}")