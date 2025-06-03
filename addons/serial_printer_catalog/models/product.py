# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # 1. Leer los parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        if not all([proxy_url, api_key, username, password]):
            raise UserError("Faltan parámetros de configuración (proxy_url, api_key, username o password)")

        # 2. Generar token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando con TopTex: {auth_response.text}")
        token = auth_response.json().get('token')

        # 3. Obtener producto NS300 con SKU corregido
        sku = 'NS300.68558_68494'
        product_url = f"{proxy_url}/v3/products/{sku}?usage_right=b2b_uniquement"
        headers['Authorization'] = f'Bearer {token}'
        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            raise UserError(f"Error al obtener el producto: {response.text}")

        data = response.json()
        _logger.info("JSON recibido desde TopTex:\n%s", data)

        # 4. Mapper TopTex -> Odoo
        name = data.get('translatedName', {}).get('es') or data.get('translatedName', {}).get('en') or 'Producto sin nombre'
        default_code = data.get('sku', sku)
        list_price = data.get('price', {}).get('netPrice', 0.0)
        description = data.get('translatedDescription', {}).get('es', '')

        # 5. Crear el producto si no existe
        existing_product = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if existing_product:
            _logger.info(f"Producto ya existe: {default_code}")
            return

        product_vals = {
            'name': name,
            'default_code': default_code,
            'list_price': list_price,
            'type': 'product',
            'description': description,
            'sale_ok': True,
            'purchase_ok': True,
        }

        new_product = self.env['product.template'].create(product_vals)
        _logger.info(f"Producto creado correctamente: {new_product.name}")