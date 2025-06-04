import json
import logging
import requests
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Parámetros del sistema
        config = self.env['ir.config_parameter'].sudo()
        api_key = config.get_param('toptex_api_key')
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        proxy_url = config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros de configuración en el sistema.")

        # Paso 1: Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        headers_auth = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        auth_data = {
            "username": username,
            "password": password
        }

        auth_response = requests.post(auth_url, headers=headers_auth, json=auth_data)
        if auth_response.status_code != 200:
            raise UserError(f"Error al autenticar: {auth_response.text}")
        token = auth_response.json().get("token")

        # Paso 2: Hacer llamada al producto NS300
        sku = "NS300.68558_68494"
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        response = requests.get(catalog_url, headers=headers)

        if response.status_code != 200:
            raise UserError(f"Error al obtener el producto: {response.text}")

        try:
            data = response.json()
        except Exception:
            raise UserError("No se pudo convertir la respuesta en JSON.")

        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        if isinstance(data, dict):
            productos = [data]
        elif isinstance(data, list):
            productos = data
        else:
            raise UserError("La API devolvió una lista vacía o un tipo de dato inesperado.")

        for producto in productos:
            name = producto.get("translatedName", {}).get("es") or producto.get("catalogReference")
            default_code = producto.get("sku")
            list_price = 10.0  # Placeholder: la API no da precio
            type_product = 'product'

            vals = {
                'name': name,
                'default_code': default_code,
                'list_price': list_price,
                'type': type_product,
            }

            existing_product = self.env['product.template'].sudo().search([('default_code', '=', default_code)], limit=1)
            if not existing_product:
                self.env['product.template'].sudo().create(vals)
                _logger.info(f"Producto creado: {name}")
            else:
                _logger.info(f"Producto ya existe: {default_code}")