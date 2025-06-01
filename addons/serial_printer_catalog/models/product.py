import requests
from odoo import models
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Validar parámetros
        if not proxy_url or not username or not password or not api_key:
            raise UserError("⚠️ Faltan parámetros del sistema: toptex_proxy_url, username, password o api_key.")

        # Generar token desde el proxy
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Accept": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error de autenticación: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió token de autenticación.")
        except Exception as e:
            raise UserError(f"❌ Excepción al autenticar: {str(e)}")

        # Hacer llamada al proxy para obtener el producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers = {
            "x-toptex-authorization": token,
            "x-api-key": api_key,
            "Accept": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto: {response.status_code} - {response.text}")

            data = response.json()
            if not data:
                raise UserError("⚠️ La respuesta está vacía o no contiene productos.")

            product_data = data[0]  # Usamos el primer producto del resultado
            self.env['product.template'].create({
                'name': product_data.get('name', 'Producto NS300'),
                'default_code': product_data.get('catalog_reference', 'NS300'),
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"❌ Excepción al obtener el producto: {str(e)}")