import logging
import requests
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Cargar parámetros de sistema
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key')
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        proxy_url = IrConfig.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise Exception("Faltan parámetros en la configuración del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {'x-api-key': api_key}
        auth_data = {"username": username, "password": password}
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_data)
        if auth_response.status_code != 200:
            raise Exception("Error de autenticación con la API de TopTex.")
        token = auth_response.json().get("token")

        # Petición del producto
        catalog_url = f"{proxy_url}/v3/products?sku=NS300.68558_68494&usage_right=b2b_uniquement"
        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token
        }
        response = requests.get(catalog_url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Error al obtener datos: {response.status_code}")

        try:
            data = response.json()
        except Exception:
            raise Exception("No se pudo convertir la respuesta a JSON.")

        # Logs para depuración
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        # Interpretar correctamente el contenido
        if isinstance(data, dict):
            if "products" in data:
                productos = data["products"]
            else:
                productos = [data]  # Producto individual
        elif isinstance(data, list):
            productos = data
        else:
            raise Exception("Respuesta inesperada de la API de TopTex (no es un dict ni una list).")

        if not productos:
            raise Exception("La API devolvió una lista vacía.")

        # Aquí puedes continuar con la lógica para crear productos en Odoo
        for producto in productos:
            _logger.info("Procesando producto: %s", producto.get("sku", "sin SKU"))
            # Crear o actualizar en product.template...

        return True