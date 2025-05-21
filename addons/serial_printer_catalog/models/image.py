# -*- coding: utf-8 -*-
import base64
import requests
from odoo import models, fields

class SerialPrinterImage(models.Model):
    _name = 'serial.printer.image'
    _description = 'Imágenes de productos desde TopTex'

    product_reference = fields.Char(string="Referencia Producto")
    image = fields.Binary(string="Imagen")

    def sync_images_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                products = response.json()
                for item in products:
                    image_url = item.get('images', {}).get('large')
                    if image_url:
                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            image_data = base64.b64encode(image_response.content)
                            self.env['serial.printer.image'].create({
                                'product_reference': item.get('reference'),
                                'image': image_data
                            })
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Fallo al sincronizar imágenes: {str(e)}")