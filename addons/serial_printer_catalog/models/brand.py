import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marca importada desde API'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex', index=True)

    @api.model
    def sync_brands_from_api(self):
        token_obj = self.env['serial.printer.token'].search([], order='create_date desc', limit=1)
        if not token_obj or not token_obj.token:
            raise UserError("Token de API no encontrado. Asegúrate de generar uno válido.")

        headers = {
            'Authorization': f'Bearer {token_obj.token}',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgidvgiZe'
        }

        url = 'https://api.toptex.io/v2/brands'
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            raise UserError(f"Error al conectar con la API: {response.status_code} - {response.text}")

        brands = response.json()
        for item in brands:
            self.env['serial.printer.brand'].sudo().update_or_create_brand(item)

    @api.model
    def update_or_create_brand(self, data):
        existing = self.search([('toptex_id', '=', data.get('id'))], limit=1)
        vals = {
            'name': data.get('name'),
            'toptex_id': data.get('id'),
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)