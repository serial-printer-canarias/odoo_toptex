from odoo import models, fields, api
import requests
import logging
from datetime import datetime, timedelta
import pytz

_logger = logging.getLogger(__name__)

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado desde la API'

    name = fields.Char(string="Nombre del producto")
    reference = fields.Char(string="Referencia")
    external_id = fields.Char(string="ID externo del producto")
    description = fields.Text(string="Descripción")
    image_url = fields.Char(string="URL de imagen")

    token = None
    token_expiry = None

    def _get_api_token(self):
        """Renueva el token si ha caducado o está a punto de caducar (menos de 10 min)."""
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        if self.token and self.token_expiry and now < self.token_expiry - timedelta(minutes=10):
            return self.token

        api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTfSOXdDvgiZe"
        username = "toes_bafaluydelreymarc"
        password = "Bafarey12345."
        url = "https://api.toptex.io/v3/authenticate"

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        payload = {
            "username": username,
            "password": password
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            _logger.error("Error al obtener token: %s", response.text)
            return None

        data = response.json()
        self.token = data.get("token")
        expiry_str = data.get("hora de caducidad")

        if self.token and expiry_str:
            self.token_expiry = datetime.strptime(expiry_str, "%Y-%m-%dT%H:%M:%S.000Z").replace(tzinfo=pytz.UTC)
            _logger.info("Token renovado correctamente. Expira en %s", self.token_expiry)
            return self.token

        return None

    @api.model
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

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            _logger.error("Error al obtener productos: %s", response.text)
            return

        products = response.json().get("data", [])
        for item in products:
            self.env['serial.printer.product'].create({
                'name': item.get('name'),
                'reference': item.get('reference'),
                'external_id': item.get('id'),
                'description': item.get('description'),
                'image_url': item.get('image_url')
            })

        _logger.info("Productos sincronizados correctamente.")