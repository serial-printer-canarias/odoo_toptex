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
            auth_url = "https://api.toptex.io/v3/authenticate"
            api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
            username = "toes_bafaluydelreymarc"
            password = "Bafarey12345."

            auth_headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            auth_payload = {
                "username": username,
                "password": password
            }

            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                _logger.error("Error autenticando: %s", auth_response.text)
                return

            token = auth_response.json().get("token")
            if not token:
                _logger.error("No se recibió token de autenticación.")
                return

            products_url = "https://api.toptex.io/api/products"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "accept": "application/json"
            }

            response = requests.get(products_url, headers=headers)
            if response.status_code == 200:
                products = response.json()
                for product in products:
                    self.env['serial.printer.product'].create({
                        'name': product.get("label"),
                        'reference': product.get("reference"),
                        'external_id': product.get("id"),
                        'description': product.get("description"),
                        'image_url': product.get("image", {}).get("url", "")
                    })
                _logger.info("Productos importados correctamente.")
            else:
                _logger.error("Error al obtener productos: %s", response.text)

        except Exception as e:
            _logger.exception("Excepción durante la sincronización de productos: %s", e)