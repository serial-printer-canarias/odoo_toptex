from odoo import models, fields, api
import requests

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto'

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código", required=True)

    @api.model
    def import_attributes_from_toptex(self):
        url = "https://api.toptex.io/products/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            attributes = response.json()
            for attr in attributes:
                self.create({
                    'name': attr.get('name', ''),
                    'code': attr.get('code', ''),
                })
        else:
            raise Exception(f"Error al conectar con TopTex: {response.status_code} - {response.text}")