import json
import logging
import requests
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_block(self, offset=0, limit=50):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')

        if not all([api_key, username, password, proxy_url]):
            raise UserError('Faltan parámetros API TopTex')

        # --- Autenticación ---
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_resp.status_code != 200:
            raise UserError(f"Error autenticando: {auth_resp.text}")
        token = auth_resp.json().get('token', '')
        headers['x-toptex-authorization'] = token

        # --- Descarga del catálogo completo ---
        catalog_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1'
        cat_resp = requests.get(catalog_url, headers=headers)
        if cat_resp.status_code != 200:
            raise UserError(f"Error obteniendo catálogo: {cat_resp.text}")
        data = cat_resp.json()
        if isinstance(data, dict) and "items" in data:
            data = data["items"]
        if not isinstance(data, list):
            raise UserError("No se obtuvo una lista de productos")

        # --- Selecciona solo el bloque ---
        bloque = data[offset:offset+limit]

        for prod in bloque:
            default_code = prod.get('catalogReference', '') or prod.get('reference', '')
            name = prod.get('designation', {}).get('es') or prod.get('designation', {}).get('en', '')
            description = prod.get('description', {}).get('es', '') or prod.get('description', {}).get('en', '')
            vals = {
                'name': name or "Sin nombre",
                'default_code': default_code or "",
                'description_sale': description,
                'type': 'consu',
                'is_storable': True,
            }
            tmpl = self.env['product.template'].sudo().search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                tmpl = self.env['product.template'].sudo().create(vals)
                _logger.info(f"➕ Producto creado: {default_code}")
            else:
                tmpl.sudo().write(vals)
                _logger.info(f"🔄 Producto actualizado: {default_code}")

        _logger.info(f"✅ FIN: Asignación de productos TopTex - bloque offset {offset}, limit {limit}.")
        return True