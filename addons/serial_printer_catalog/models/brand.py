
import requests
from odoo import models, fields

class SerialPrinterBrand(models.Model):
    _name = 'serial_printer.brand'
    _description = 'Marca externa'

    name = fields.Char(string="Nombre", required=True)

    def import_toptex_brands(self):
        url = "https://api.toptex.io/v3/attributes"
        headers = {
            "accept": "application/json",
            "x-api-key": "qh7SERVyz43xDDNaRONs0aLxGntfFSOX4b0vgiZe"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error al conectar con la API: {response.status_code} - {response.text}")

        data = response.json()
        total = 0
        for attribute in data:
            if attribute.get("code") == "brand":
                for brand in attribute.get("values", []):
                    name = brand.get("label")
                    if name:
                        self.env['serial_printer.brand'].sudo()._update_or_create_brand(name)
                        total += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{total} marcas importadas desde la API',
                'type': 'success',
                'sticky': False,
            }
        }

    @classmethod
    def _update_or_create_brand(cls, env, name):
        existing = env['serial_printer.brand'].search([('name', '=', name)], limit=1)
        if existing:
            existing.write({'name': name})
        else:
            env['serial_printer.brand'].create({'name': name})
