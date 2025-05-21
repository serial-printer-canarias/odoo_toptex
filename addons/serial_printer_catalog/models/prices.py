# -*- coding: utf-8 -*-
import requests
from odoo import models, fields

class SerialPrinterPrice(models.Model):
    _name = 'serial.printer.price'
    _description = 'Precio personalizado desde API TopTex'

    product_reference = fields.Char(string="Referencia Producto")
    client_reference = fields.Char(string="Cliente")
    price = fields.Float(string="Precio Personalizado")

    def sync_prices_from_api(self):
        url = "https://api.toptex.io/api/prices"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    self.env['serial.printer.price'].create({
                        'product_reference': item.get('reference'),
                        'client_reference': item.get('client'),
                        'price': item.get('price')
                    })
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Fallo al sincronizar precios: {str(e)}")