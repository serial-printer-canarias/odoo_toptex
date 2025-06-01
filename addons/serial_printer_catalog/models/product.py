import requests
from odoo import models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        def get_param(key):
            return self.env['ir.config_parameter'].sudo().get_param(key)

        # Obtener credenciales
        username = get_param("toptex_username")
        password = get_param("toptex_password")
        api_key = get_param("toptex_api_key")

        if not username or not password or not api_key:
            raise ValueError("Faltan credenciales en parámetros del sistema.")

        # Paso 1: Obtener token
        auth_url = "https://api.toptex.io/v3/authenticate"
        headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }
        data = {
            "username": username,
            "password": password
        }

        response = requests.post(auth_url, headers=headers, json=data)
        if response.status_code != 200:
            raise ValueError(f"Error al obtener token: {response.status_code} – {response.text}")

        token = response.json().get("token")
        if not token:
            raise ValueError("No se recibió token válido desde TopTex")

        # Paso 2: Obtener datos del producto NS300
        catalog_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        catalog_headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }

        product_response = requests.get(catalog_url, headers=catalog_headers)
        if product_response.status_code != 200:
            raise ValueError(f"Error al obtener producto: {product_response.status_code} – {product_response.text}")

        product_data = product_response.json()
        if not isinstance(product_data, list) or not product_data:
            raise ValueError("Respuesta de TopTex vacía o inválida")

        # Crear producto en Odoo
        for product in product_data:
            name = product.get("label")
            reference = product.get("catalogReference")

            if not name or not reference:
                continue

            existing = self.env['product.template'].search([('default_code', '=', reference)], limit=1)
            if not existing:
                self.env['product.template'].create({
                    "name": name,
                    "default_code": reference,
                    "type": "product",
                })