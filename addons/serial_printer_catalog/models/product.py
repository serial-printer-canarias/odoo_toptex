import requests
from odoo import models
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_products_from_api(self):
        # Obtener parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        # URL de autenticación
        auth_url = f"{proxy_url}/v3/authenticate"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,  # ✅ API key como header, igual que en Postman
            "Accept-Encoding": "identity"
        }

        auth_data = {
            "username": username,
            "password": password
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers=headers)
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
        except Exception as e:
            raise UserError(f"Error al obtener el token de TopTex: {e}")

        # Llamada al producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers.update({
            "Authorization": f"Bearer {token}"
        })

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            product_data = response.json()

            self.create({
                'name': product_data.get('name', 'NS300'),
                'default_code': product_data.get('reference'),
                'type': 'product',
                'list_price': 0.0,
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"Error al sincronizar producto NS300 de TopTex: {e}")