import requests
from odoo import models, fields
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
            raise UserError("⚠️ Faltan parámetros del sistema: toptex_proxy_url, username, password o api_key.")

        # 1. Obtener token de autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error al autenticar: {auth_response.status_code} -> {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió token de autenticación.")
        except Exception as e:
            raise UserError(f"❌ Excepción al autenticar: {str(e)}")

        # 2. Obtener datos del producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement&display_prices=1"
        headers = {
            "x-toptex-authorization": token,
            "x-api-key": api_key,
            "Accept": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto: {response.status_code} -> {response.text}")
            data = response.json()
            if not data:
                raise UserError("⚠️ La respuesta está vacía.")
        except Exception as e:
            raise UserError(f"❌ Excepción al obtener el producto: {str(e)}")

        # 3. Buscar el producto NS300 dentro del JSON
        producto = None
        if isinstance(data, dict):
            producto = data.get('NS300')
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get('catalogReference') == 'NS300':
                    producto = item
                    break

        if not producto:
            raise UserError("⚠️ No se encontró el producto NS300 en la respuesta.")

        # 4. Crear producto en Odoo (base)
        self.env['product.template'].create({
            'name': f"Producto NS300",
            'default_code': producto.get('catalogReference', 'NS300'),
            'sale_ok': True,
            'purchase_ok': True,
        })