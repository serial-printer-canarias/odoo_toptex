from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado desde la API'

    name = fields.Char(string="Nombre del producto")
    reference = fields.Char(string="Referencia")
    external_id = fields.Char(string="ID externo del producto")
    description = fields.Text(string="Descripción")
    image_url = fields.Char(string="URL de imagen")

    @api.model
    def sync_products_from_api(self):
        try:
            # Autenticación
            auth_url = "https://api.toptex.io/v3/authenticate"
            api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
            username = "toes_bafaluydelreymarc"
            password = "Bafarey12345."

            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "accept": "application/json"
            }

            auth_payload = {
                "username": username,
                "password": password
            }

            auth_response = requests.post(auth_url, json=auth_payload, headers=headers)
            if auth_response.status_code != 200:
                _logger.error("Error de autenticación: %s", auth_response.text)
                return

            token = auth_response.json().get("token")
            if not token:
                _logger.error("Token no recibido: %s", auth_response.text)
                return

            # Obtener productos
            products_url = "https://api.toptex.io/v3/products"
            product_headers = {
                "Authorization": f"Bearer {token}",
                "x-api-key": api_key,
                "Accept": "application/json"
            }

            product_response = requests.get(products_url, headers=product_headers)
            if product_response.status_code != 200:
                _logger.error("Error obteniendo productos: %s", product_response.text)
                return

            products = product_response.json().get("data", [])
            for product in products:
                self.create_or_update_product(product)

        except Exception as e:
            _logger.exception("Error al sincronizar productos desde la API: %s", str(e))

    def create_or_update_product(self, product_data):
        reference = product_data.get("reference")
        name = product_data.get("name")
        description = product_data.get("description")
        external_id = str(product_data.get("id"))
        image_url = product_data.get("images", {}).get("front")

        existing = self.search([('external_id', '=', external_id)], limit=1)
        values = {
            'name': name,
            'reference': reference,
            'description': description,
            'external_id': external_id,
            'image_url': image_url,
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)