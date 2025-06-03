import requests
from odoo import models, fields, api
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
            raise UserError("Faltan parámetros de configuración para la API de TopTex.")

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token de autenticación.")

        # Llamar a producto por SKU (producto simple NS300 en este caso)
        catalog_url = f"{proxy_url}/v3/products?sku=NS300.68558_68494&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError("No se pudo recuperar el producto desde la API de TopTex.")

        data = response.json()

        # Si es dict (respuesta por SKU), lo convertimos en lista
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise UserError("Respuesta inesperada de la API de TopTex (ni dict ni lista).")

        # Filtrar por catalogReference
        productos_ns300 = [prod for prod in data if prod.get('catalogReference') == 'NS300']
        if not productos_ns300:
            raise UserError("No se encontró el producto NS300 en la respuesta.")

        producto = productos_ns300[0]

        # Crear producto en Odoo (básico)
        self.env['product.template'].create({
            'name': producto.get('label', 'Producto sin nombre'),
            'default_code': producto.get('sku'),
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
        })