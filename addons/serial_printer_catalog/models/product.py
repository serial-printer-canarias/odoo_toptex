import json
import logging
import requests

from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Recuperar parámetros del sistema
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        proxy_url = IrConfigParam.get_param('toptex_proxy_url')
        api_key = IrConfigParam.get_param('toptex_api_key')
        auth_token = IrConfigParam.get_param('toptex_token')

        if not all([proxy_url, api_key, auth_token]):
            raise Exception("Faltan parámetros de configuración (proxy_url, api_key o token).")

        # Construir la URL con un SKU válido y real (ajústalo si deseas otro producto)
        catalog_url = f"{proxy_url}/v3/products?sku=NS300.68558_68494&usage_right=b2b_uniquement"

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": auth_token,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        # Hacemos la petición
        response = requests.get(catalog_url, headers=headers)

        if response.status_code != 200:
            raise Exception("Error al obtener datos de la API")

        try:
            data = response.json()
        except Exception:
            raise Exception("No se pudo convertir la respuesta a JSON")

        # Log para depuración
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        # Interpretamos el contenido correctamente
        if isinstance(data, dict):
            if "products" in data:
                productos = data["products"]
            else:
                productos = [data]  # Es un producto único
        elif isinstance(data, list):
            productos = data
        else:
            raise Exception("Respuesta inesperada de la API: no es ni dict ni list")

        if not productos:
            raise Exception("La API devolvió una lista vacía.")

        # Aquí puedes continuar creando productos en Odoo a partir de `productos`
        for producto in productos:
            nombre = producto.get('catalogReference', 'Sin nombre')
            _logger.info("Creando producto: %s", nombre)

            self.env['product.template'].create({
                'name': nombre,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })