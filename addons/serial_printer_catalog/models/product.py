import requests
import logging
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Obtener parámetros de configuración
        config = self.env['ir.config_parameter'].sudo()
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        api_key = config.get_param('toptex_api_key')
        proxy_url = config.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("Faltan parámetros de configuración para la API de TopTex.")

        # Autenticación y obtención del token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error al autenticar con TopTex: {auth_response.text}")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió un token válido de TopTex.")

        # Construir la URL del producto
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        _logger.info("URL solicitada: %s", product_url)

        response = requests.get(product_url, headers=headers)
        _logger.info("Código de estado: %s", response.status_code)
        _logger.info("Contenido recibido: %s", response.text)

        if response.status_code != 200:
            raise UserError(f"Error al obtener el producto: {response.text}")

        try:
            data = response.json()
        except Exception as e:
            raise UserError(f"No se pudo interpretar la respuesta JSON: {e}")

        if isinstance(data, dict):
            productos = [data]
        elif isinstance(data, list):
            productos = data
        else:
            raise UserError("La API devolvió una estructura de datos inesperada.")

        for producto in productos:
            name = producto.get("translatedName", {}).get("es") or producto.get("catalogReference")
            default_code = producto.get("sku")
            list_price = producto.get("publicPrice", 0.0)

            if not name or not default_code:
                _logger.warning("Producto ignorado por falta de campos obligatorios: %s", producto)
                continue

            # Verificar si el producto ya existe
            existing_product = self.env["product.template"].search([('default_code', '=', default_code)], limit=1)
            if existing_product:
                _logger.info("El producto con SKU %s ya existe.", default_code)
                continue

            # Crear el producto
            self.env["product.template"].create({
                "name": name,
                "default_code": default_code,
                "list_price": list_price,
                "type": "product",
                "sale_ok": True,
                "purchase_ok": True,
            })
            _logger.info("Producto %s creado correctamente.", name)