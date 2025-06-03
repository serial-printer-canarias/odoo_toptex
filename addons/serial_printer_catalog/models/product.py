import requests
from odoo import models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Recuperar credenciales desde parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("Faltan parámetros del sistema (usuario, contraseña, API key o proxy).")

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key}

        token_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if token_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")

        token = token_response.json().get("token")
        if not token:
            raise UserError("No se recibió token de autenticación.")

        # Llamada al producto por SKU
        sku = "NS300.68558_684948"
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError("No se pudo recuperar el producto desde la API de TopTex.")

        try:
            data = response.json()
        except Exception:
            raise UserError("La respuesta de la API no es JSON válido.")

        # Analizar tipo de respuesta
        if isinstance(data, list):
            if not data:
                raise UserError("La API devolvió una lista vacía.")
            product_data = data[0]
        elif isinstance(data, dict):
            product_data = data
        else:
            raise UserError("Respuesta inesperada de la API de TopTex (ni lista ni dict).")

        # Confirmar que es el producto esperado
        catalog_ref = product_data.get('catalogReference')
        if not catalog_ref or catalog_ref.upper() != 'NS300':
            raise UserError("No se encontró el producto NS300 en la respuesta.")

        # Crear producto en Odoo
        self.env['product.template'].create({
            'name': product_data.get('designation', {}).get('es', 'NS300'),
            'default_code': catalog_ref,
            'type': 'product',
        })