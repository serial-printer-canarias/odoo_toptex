from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Brand from TopTex'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código', required=True)

    @api.model
    def sync_brands_from_api(self):
        url = "https://api.toptex.com/api/brands"
        headers = {
            "Authorization": "Bearer qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)

        _logger.info("TopTex API Response status: %s", response.status_code)
        _logger.info("TopTex API Response JSON: %s", response.text)