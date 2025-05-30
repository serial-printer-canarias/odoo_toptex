import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductSync(models.TransientModel):
    _name = 'product.sync.toptex'
    _description = 'Sincronizar producto desde TopTex'

    @api.model
    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(_("Falta el parámetro de sistema: %s") % key)
        return param

    @api.model
    def sync_ns300_toptex(self):
        # 1. Obtener credenciales desde parámetros del sistema
        api_key = self._get_toptex_credential('toptex_api_key')
        username = self._get_toptex_credential('toptex_username')
        password = self._get_toptex_credential('toptex_password')

        # 2. Autenticación para obtener token
        auth_url = "https://api.toptex.io/v3/authenticate"
        auth_headers = {
            "x-api-key": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }
        payload = {
            "username": username,
            "password": password
        }

        response = requests.post(auth_url, json=payload, headers=auth_headers)
        if response.status_code != 200:
            raise UserError("Error al autenticar con TopTex: %s" % response.text)

        token = response.json().get('token')
        if not token:
            raise UserError("Token vacío recibido desde TopTex.")

        # 3. Obtener producto NS300
        product_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }

        res = requests.get(product_url, headers=headers)
        if res.status_code != 200:
            raise UserError("Error al obtener producto NS300: %s" % res.text)

        data = res.json()
        if not data or not isinstance(data, list):
            raise UserError("Respuesta inválida o vacía de TopTex")

        for item in data:
            name = item.get("label")
            reference = item.get("catalogReference")

            if not name or not reference:
                continue

            # Verificar si ya existe
            existing = self.env['product.template'].search([('default_code', '=', reference)])
            if not existing:
                self.env['product.template'].create({
                    'name': name,
                    'default_code': reference,
                    'type': 'product'
                })