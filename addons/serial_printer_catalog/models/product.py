import requests
from odoo import models
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_products_from_api(self):
        # Parámetros del sistema
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        # Autenticación directa
        auth_url = "https://api.toptex.io/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers={"Content-Type": "application/json"})
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
        except Exception as e:
            raise UserError(f"Error al obtener el token de TopTex: {e}")

        # Llamada directa al producto NS300
        product_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Encoding": "identity"
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            product_data = response.json()

            # Crear producto básico (adapta si hace falta)
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