import requests
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ToptexAPIMixin(models.AbstractModel):
    _name = 'toptex.api.mixin'
    _description = 'Conector API Toptex'

    def fetch_toptex_brands(self):
        url = "https://api.toptex.io/v2/brands"
        headers = {
            "X-AUTH-TOKEN": "AQUI_TU_API_KEY",  # <- REEMPLAZA POR TU API KEY
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            _logger.error(f"Error al conectar con Toptex: {response.status_code} - {response.text}")
            return []

    def import_toptex_brands(self):
        brands = self.fetch_toptex_brands()
        Brand = self.env['toptex.brand']
        for brand in brands:
            Brand.sudo().create({
                'name': brand.get('name'),
                'toptex_id': brand.get('id')
            })
        _logger.info(f"Se importaron {len(brands)} marcas desde Toptex.")