import requests
from odoo import models, fields

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributos de TopTex'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)

    def sync_attributes_from_api(self):
        url = "https://api.toptex.io/v3/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            for attr in data:
                self.env['serial.printer.attribute'].sudo().update_or_create({
                    'code': attr.get('code')
                }, {
                    'name': attr.get('name'),
                    'code': attr.get('code')
                })

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al conectar con la API de TopTex (atributos): {e}")