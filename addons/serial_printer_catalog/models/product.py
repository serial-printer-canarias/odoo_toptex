import os
import requests
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ProductSync(models.Model):
    _name = "serial_printer_catalog.product"
    _description = "Product Sync from TopTex"

    def _get_system_param(self, key_name):
        return self.env['ir.config_parameter'].sudo().get_param(key_name)

    def _generate_token(self):
        """Solicita el token de autenticación a través del proxy."""
        proxy_url = "https://toptex-proxy.onrender.com/proxy"
        url_auth = "https://api.toptex.com/v3/token"

        headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",  # evita gzip
            "Accept": "application/json"
        }
        data = {
            "username": self._get_system_param("toptex_username"),
            "password": self._get_system_param("toptex_password")
        }

        try:
            response = requests.post(
                proxy_url,
                params={"url": url_auth},
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("token")
        except Exception as e:
            _logger.error(f"Error al obtener el token de TopTex: {str(e)}")
            raise

    def sync_products_from_api(self):
        """Sincroniza todos los productos del catálogo TopTex."""
        proxy_url = "https://toptex-proxy.onrender.com/proxy"
        toptex_api_key = self._get_system_param("toptex_api_key")
        token = self._generate_token()

        url_products = (
            "https://api.toptex.com/v3/products?"
            "usage_right=b2b_uniquement&result_in_file=1"
        )

        headers = {
            "x-api-key": toptex_api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "identity",  # importante para evitar errores gzip
            "Accept": "application/json"
        }

        try:
            response = requests.get(
                proxy_url,
                params={"url": url_products},
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            _logger.info(f"Productos recibidos de TopTex: {len(data)} elementos")
            # Aquí puedes procesar los productos como necesites...
        except Exception as e:
            _logger.error(f"Error al sincronizar productos de TopTex: {str(e)}")
            raise