from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante sincronizada desde la API'

    name = fields.Char(string="Nombre de la variante")
    toptex_id = fields.Char(string="ID TopTex")
    product_template_id = fields.Many2one('product.template', string="Producto asociado")
    attribute_ids = fields.Many2many('product.attribute', string="Atributos")

    @api.model
    def sync_variants_from_api(self):
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

            variants_url = "https://api.toptex.io/api/variants"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "accept": "application/json"
            }

            response = requests.get(variants_url, headers=headers)
            if response.status_code == 200:
                variants = response.json()
                for variant in variants:
                    self.env['serial.printer.variant'].create({
                        'name': variant.get("label"),
                        'toptex_id': variant.get("id")
                        # No asociamos product_template ni attributes automáticamente aquí aún
                    })
                _logger.info("Variantes importadas correctamente.")
            else:
                _logger.error("Error al obtener variantes: %s", response.text)

        except Exception as e:
            _logger.exception("Excepción durante la sincronización de variantes: %s", e)