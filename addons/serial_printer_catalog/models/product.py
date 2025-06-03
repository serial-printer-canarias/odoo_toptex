import requests
from odoo import models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_param('toptex_api_key')
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros del sistema para conectar con la API de TopTex.")

        # Paso 1: Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key}

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token de autenticación.")

        # Paso 2: Llamada al producto NS300
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?sku=NS300.68558.68494&usage_right=b2b_uniquement"

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError("Error al recuperar el producto desde la API de TopTex.")

        try:
            data = response.json()
        except Exception as e:
            raise UserError(f"No se pudo interpretar la respuesta JSON: {e}")

        # Validación del tipo de respuesta
        if isinstance(data, list):
            if not data:
                raise UserError("La API devolvió una lista vacía.")
            product_data = data[0]
        elif isinstance(data, dict):
            product_data = data
        else:
            raise UserError("Respuesta inesperada de la API de TopTex (no es un dict ni lista válida).")

        # Validamos el producto NS300
        if product_data.get("catalogReference") != catalog_reference:
            raise UserError("No se encontró el producto NS300 en la respuesta.")

        # Crear el producto en Odoo
        self.create({
            'name': product_data.get("label", "Sin nombre"),
            'default_code': product_data.get("sku", "Sin SKU"),
            'type': 'product',
        })