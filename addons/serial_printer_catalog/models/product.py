import requests
from odoo import models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Obtener credenciales de parámetros del sistema
        config = self.env['ir.config_parameter'].sudo()
        api_key = config.get_param('toptex_api_key')
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        proxy_url = config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan credenciales o URL del proxy en los parámetros del sistema.")

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

        # Paso 2: Obtener un producto por SKU
        sku = "NS300.68558_684948"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        product_response = requests.get(product_url, headers=headers)
        if product_response.status_code != 200:
            raise UserError("No se pudo recuperar el producto desde la API de TopTex.")

        data = product_response.json()
        if not isinstance(data, dict):
            raise UserError("Respuesta inesperada de la API de TopTex (no es un dict).")

        # Crear el producto en Odoo
        name = data.get("designation", {}).get("es") or data.get("designation", {}).get("en") or "Producto TopTex"
        default_code = data.get("sku", sku)
        description = data.get("description", {}).get("es") or data.get("description", {}).get("en") or ""

        existing_product = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if not existing_product:
            self.env['product.template'].create({
                'name': name,
                'default_code': default_code,
                'type': 'product',
                'detailed_type': 'product',
                'description_sale': description,
            })
        else:
            existing_product.write({
                'name': name,
                'description_sale': description,
            })