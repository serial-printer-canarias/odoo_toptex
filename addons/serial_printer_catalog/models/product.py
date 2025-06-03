import requests
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Recuperar parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        api_key = ir_config.get_param('toptex_api_key')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        # Obtener el token de autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
        if auth_response.status_code != 200:
            raise Exception("Error al obtener el token de autenticación.")

        token = auth_response.json().get("token")
        if not token:
            raise Exception("Token no encontrado en la respuesta de autenticación.")

        # Petición al catálogo por SKU específico
        sku = "NS300.68558_68494"
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        catalog_headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        response = requests.get(catalog_url, headers=catalog_headers)
        if response.status_code != 200:
            raise Exception("Error al obtener datos del catálogo.")

        try:
            data = response.json()
        except Exception:
            raise Exception("No se pudo convertir la respuesta a JSON.")

        # Log del tipo y contenido para depurar
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        # Interpretación del contenido
        if isinstance(data, dict):
            productos = [data]
        elif isinstance(data, list):
            if not data:
                raise Exception("La API devolvió una lista vacía.")
            productos = data
        else:
            raise Exception("Respuesta inesperada de la API de TopTex (no es un dict ni lista).")

        # Crear productos (solo nombre de prueba)
        for prod in productos:
            name = prod.get('catalogReference', 'Producto sin nombre')
            if not self.env['product.template'].search([('name', '=', name)]):
                self.env['product.template'].create({
                    'name': name,
                    'type': 'product',
                })
                _logger.info("Producto creado: %s", name)
            else:
                _logger.info("Producto ya existente: %s", name)