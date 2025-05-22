import requests
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string="ID TopTex", readonly=True)

class ToptexProductSync(models.Model):
    _name = 'serial_printer_catalog.product_sync'
    _description = 'Sincronización de productos desde TopTex'

    @api.model
    def authenticate_and_get_token(self):
        auth_url = "https://api.toptex.io/v3/authenticate"
        api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        username = "toes_bafaluydelreymarc"
        password = "Bafarey12345."

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "username": username,
            "password": password
        }

        try:
            response = requests.post(auth_url, json=payload, headers=headers)
            if response.status_code == 200:
                token = response.json().get("token")
                _logger.info("Token obtenido correctamente.")
                return token
            else:
                _logger.error(f"Error al obtener token: {response.text}")
        except Exception as e:
            _logger.error(f"Excepción al autenticar: {str(e)}")
        return None

    @api.model
    def sync_toptex_products(self):
        api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        token = self.authenticate_and_get_token()

        if not token:
            _logger.error("No se pudo obtener el token. Abortando sincronización.")
            return

        url = "https://api.toptex.io/v3/products"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                products = response.json()
                for item in products:
                    self.env['product.template'].create({
                        'name': item.get('label'),
                        'default_code': item.get('reference'),
                        'toptex_id': item.get('id'),
                    })
                _logger.info("Productos importados correctamente.")
            else:
                _logger.error(f"Error al obtener productos: {response.text}")
        except Exception as e:
            _logger.error(f"Excepción al sincronizar productos: {str(e)}")