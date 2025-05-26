import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto del catálogo'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    reference = fields.Char(string='Referencia')
    description = fields.Text(string='Descripción')

    @api.model
    def sync_products_from_api(self):
        token_record = self.env['serial.printer.token'].search([], limit=1)
        if not token_record:
            raise UserError("Token de API no encontrado. Asegúrate de generar uno válido.")
        
        token = token_record.get_valid_token()

        url = 'https://api.toptex.io/v3/products'
        headers = {
            'Authorization': f'Bearer {token}',
            'x-api-key': token_record.api_key
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for product in data.get('items', []):
                self.create_or_update_product(product)
        else:
            raise UserError(f"Error al obtener productos: {response.status_code} - {response.text}")

    def create_or_update_product(self, product_data):
        toptex_id = product_data.get('id')
        product = self.search([('toptex_id', '=', toptex_id)], limit=1)

        values = {
            'name': product_data.get('name', ''),
            'toptex_id': toptex_id,
            'reference': product_data.get('reference', ''),
            'description': product_data.get('description', ''),
        }

        if product:
            product.write(values)
        else:
            self.create(values)