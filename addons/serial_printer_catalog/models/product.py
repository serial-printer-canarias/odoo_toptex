from odoo import models, fields, api
import requests
import logging
from datetime import datetime, timedelta
import pytz

_logger = logging.getLogger(__name__)


class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado desde TopTex'

    name = fields.Char(string="Nombre del producto")
    reference = fields.Char(string="Referencia")
    external_id = fields.Char(string="ID externo")
    description = fields.Text(string="Descripción")
    image_url = fields.Char(string="URL de imagen")

    token = None
    token_expiry = None

    def _get_api_token(self):
        """Renueva el token si ha caducado"""
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        if self.token and self.token_expiry and now < self.token_expiry:
            return self.token

        api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        username = "toes_bafaluydelreymarc"
        password = "Bafarey12345."
        url = "https://api.toptex.io/v3/authenticate"

        headers = {
            "x-api-key": api_key,
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "username": username,
            "password": password
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("token")
                expires_in = token_data.get("expiresIn", 3600)
                self.token_expiry = now + timedelta(seconds=expires_in)
                _logger.info("Token renovado correctamente")
                return self.token
            else:
                _logger.error(f"No se pudo obtener el token: {response.status_code} - {response.text}")
        except Exception as e:
            _logger.error(f"Excepción al obtener el token: {str(e)}")
        return None

    def sync_products_from_api(self):
        token = self._get_api_token()
        if not token:
            _logger.error("No se pudo obtener el token. Cancelando sincronización.")
            return

        url = "https://api.toptex.io/v3/products"
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                _logger.error(f"Error al obtener productos: {response.status_code} - {response.text}")
                return

            products = response.json().get("data", [])
            for item in products:
                self.env['serial.printer.product'].create({
                    'name': item.get('name'),
                    'reference': item.get('reference'),
                    'external_id': item.get('id'),
                    'description': item.get('description'),
                    'image_url': item.get('image_url'),
                })
            _logger.info("Productos sincronizados correctamente")
        except Exception as e:
            _logger.error(f"Excepción durante la sincronización de productos: {str(e)}")