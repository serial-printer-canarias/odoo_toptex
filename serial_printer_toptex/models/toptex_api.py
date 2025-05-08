import requests
from odoo import models

class ToptexAPIMixin(models.AbstractModel):
    _name = 'toptex.api.mixin'
    _description = 'Toptex API Mixin'

    def fetch_toptex_brands(self):
        url = "https://api.toptex.io/v2/brands"
        headers = {
            "X-AUTH-TOKEN": "TU_TOKEN_API",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error al conectar: {response.status_code} - {response.text}")