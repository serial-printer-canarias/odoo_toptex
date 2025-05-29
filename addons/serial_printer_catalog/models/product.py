import json
import requests
from odoo import models
from odoo.exceptions import UserError


class SerialPrinterProduct(models.Model):
    _inherit = 'product.template'

    def _get_toptex_credentials(self):
        """Leer credenciales desde parámetros del sistema."""
        param_model = self.env['ir.config_parameter'].sudo()
        return {
            "username": param_model.get_param('toptex_username'),
            "password": param_model.get_param('toptex_password'),
            "api_key": param_model.get_param('toptex_api_key')
        }

    def _generate_token(self):
        """Llama al proxy para obtener el token de autenticación."""
        proxy_url = "https://toptex-proxy.onrender.com/proxy"
        toptex_auth_url = "https://api.toptex.com/v3/login"

        credentials = self._get_toptex_credentials()
        headers = {
            "x-api-key": credentials["api_key"],
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",  # evitar gzip
            "Accept": "application/json",
        }
        body = {
            "username": credentials["username"],
            "password": credentials["password"]
        }

        response = requests.post(
            proxy_url,
            params={"url": toptex_auth_url},
            headers=headers,
            json=body,
            timeout=30
        )

        if response.status_code == 200:
            return response.json().get("token")
        raise UserError(f"❌ Error generando token: {response.status_code} - {response.text}")

    def sync_products_from_api(self):
        """Sincroniza todo el catálogo de productos desde TopTex vía proxy."""
        proxy_url = "https://toptex-proxy.onrender.com/proxy"
        catalog_url = "https://api.toptex.com/v3/products?usage_right=b2b_uniquement&result_in_file=1"

        credentials = self._get_toptex_credentials()
        token = self._generate_token()

        headers = {
            "x-api-key": credentials["api_key"],
            "x-toptex-authorization": token,
            "Accept-Encoding": "identity",  # evita errores gzip
            "Accept": "application/json",
        }

        response = requests.get(
            proxy_url,
            params={"url": catalog_url},
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener productos: {response.status_code} - {response.text}")

        data = response.json()
        # Aquí puedes procesar cada producto como necesites
        for product in data.get("products", []):
            self._process_product(product)

    def _process_product(self, product_data):
        """Ejemplo básico de procesamiento."""
        sku = product_data.get("sku")
        name = product_data.get("name", {}).get("es") or product_data.get("name", {}).get("en")

        if not sku:
            return  # Ignorar si no tiene SKU

        self.env['product.template'].sudo().create({
            'name': name,
            'default_code': sku,
            # Agrega aquí más campos si los necesitas
        })