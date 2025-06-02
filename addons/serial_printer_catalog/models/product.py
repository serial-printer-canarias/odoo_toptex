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

        if not all([proxy_url, username, password, api_key]):
            raise UserError("❌ Faltan parámetros del sistema: toptex_proxy_url, username, password o api_key.")

        # Autenticación para obtener el token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticación: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió token.")
        except Exception as e:
            raise UserError(f"❌ Excepción autenticación: {str(e)}")

        # Llamada para obtener el producto NS300
        product_url = f"{proxy_url}/v3/products"
        params = {
            "catalog_reference": "ns300",
            "usage_right": "b2b_uniquement",
            "display_prices": "1",
            "lang": "es"
        }
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers, params=params)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto: {response.status_code} - {response.text}")

            data = response.json()
            if not data:
                raise UserError("⚠️ La respuesta está vacía o no contiene datos.")

            # Comprobamos si el NS300 está en la respuesta
            ns300_data = data.get("forAdults", [])
            ns300 = None
            for item in ns300_data:
                if item == "NS300" or (isinstance(item, dict) and item.get("catalogReference") == "NS300"):
                    ns300 = item
                    break

            if not ns300:
                raise UserError("⚠️ No se encontró el producto NS300 en la respuesta.")

            # Crear el producto básico
            self.env['product.template'].create({
                'name': "Producto NS300",
                'default_code': "NS300",
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"❌ Excepción al procesar producto: {str(e)}")