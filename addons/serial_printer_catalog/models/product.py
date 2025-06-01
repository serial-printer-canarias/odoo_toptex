import requests
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            raise UserError("⚠️ Faltan parámetros del sistema: proxy_url, username, password o api_key.")

        # Generar token desde el proxy
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        auth_data = {
            "username": username,
            "password": password
        }

        try:
            auth_response = requests.post(auth_url, headers=auth_headers, json=auth_data)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error al autenticar: {auth_response.status_code} - {auth_response.text}")

            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ Token vacío en la respuesta del proxy.")

            # Llamar a la API del producto NS300
            product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
            product_headers = {
                "x-toptex-authorization": token,
                "x-api-key": api_key,
                "Accept": "application/json"
            }

            product_response = requests.get(product_url, headers=product_headers)
            if product_response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto NS300: {product_response.status_code} - {product_response.text}")

            data = product_response.json()
            if not data:
                raise UserError("⚠️ La API devolvió una respuesta vacía.")

            product_data = data[0]

            # Crear producto en product.template
            self.env['product.template'].create({
                'name': product_data.get('name', 'Producto NS300'),
                'default_code': product_data.get('catalog_reference', 'NS300'),
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"❌ Excepción al conectar con TopTex: {str(e)}")