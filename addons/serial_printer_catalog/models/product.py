import json
import logging
import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_products_from_api(self):
        # 1. Leer credenciales y proxy desde parámetros del sistema
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise Exception("Faltan credenciales o URL del proxy en los parámetros del sistema.")

        # 2. Obtener token de autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key
        }
        response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if response.status_code != 200:
            raise Exception("Error al autenticar con la API de TopTex.")

        token = response.json().get("token")
        if not token:
            raise Exception("No se recibió token de autenticación.")

        # 3. Consultar producto NS300 individual
        catalog_url = f"{proxy_url}/v3/products?sku=NS300.68558_684948&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise Exception("Error al obtener datos de producto desde la API.")

        # 4. Interpretar la respuesta
        try:
            data = response.json()
        except Exception:
            raise Exception("No se pudo convertir la respuesta a JSON.")

        # Log útil para debug
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        if isinstance(data, dict):
            if "products" in data:
                productos = data["products"]
            else:
                productos = [data]
        elif isinstance(data, list):
            productos = data
        else:
            raise Exception("Respuesta inesperada de la API de TopTex (no es lista ni diccionario).")

        if not productos:
            raise Exception("La API devolvió una lista vacía.")

        # 5. Buscar el producto NS300
        producto_ns300 = None
        for prod in productos:
            if prod.get("catalogReference") == "NS300":
                producto_ns300 = prod
                break

        if not producto_ns300:
            raise Exception("No se encontró el producto NS300 en la respuesta.")

        # 6. Crear producto en Odoo si no existe
        existing_product = self.env['product.template'].search([
            ('default_code', '=', producto_ns300.get("sku"))
        ], limit=1)

        if existing_product:
            _logger.info("El producto NS300 ya existe en Odoo.")
            return

        self.env['product.template'].create({
            'name': producto_ns300.get("designation", "Producto NS300"),
            'default_code': producto_ns300.get("sku", "NS300"),
            'type': 'product',
            'list_price': 0.0,
            'standard_price': 0.0,
            'sale_ok': True,
            'purchase_ok': True,
        })

        _logger.info("Producto NS300 creado correctamente en Odoo.")