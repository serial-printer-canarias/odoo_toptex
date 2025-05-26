import requests
from odoo import models, fields, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="TopTex ID")
    toptex_code = fields.Char(string="TopTex Code")

    def get_valid_token(self):
        token_record = self.env['serial.printer.token'].search([], limit=1)
        if not token_record or not token_record.token:
            raise UserError(_("Token de API no encontrado. Asegúrate de generar uno válido."))
        return token_record.token

    def sync_products_from_api(self):
        base_url = 'https://api.toptex.io/v3/products'
        token = self.get_valid_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizEdvgiZe',
        }

        try:
            response = requests.get(base_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error al conectar con la API de TopTex: {str(e)}")
            raise UserError(_("Error al conectar con la API de TopTex."))

        data = response.json()

        for item in data.get("products", []):
            product_code = item.get("code")
            existing_product = self.search([('toptex_code', '=', product_code)], limit=1)

            values = {
                'name': item.get("label"),
                'toptex_id': item.get("id"),
                'toptex_code': product_code,
                'list_price': item.get("publicPrice", 0.0),
                'standard_price': item.get("costPrice", 0.0),
            }

            if existing_product:
                existing_product.write(values)
            else:
                self.create(values)