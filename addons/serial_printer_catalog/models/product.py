# -*- coding: utf-8 -*-
import requests
from odoo import models, fields
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char(string='ID TopTex')

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no configurado")
        return param

    def _generate_token(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token_url = "https://api.toptex.io/v3/authenticate"
        headers = {
            "x-api-key": self._get_toptex_credential('toptex_api_key'),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        data = {
            "username": self._get_toptex_credential('toptex_username'),
            "password": self._get_toptex_credential('toptex_password'),
        }
        response = requests.post(
            proxy_url,
            params={"url": token_url},
            headers=headers,
            json=data,
        )
        if response.status_code == 200:
            return response.json().get("token")
        raise UserError(f"Error al generar token TopTex: {response.text}")

    def sync_toptex_product(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token = self._generate_token()
        product_url = (
            "https://api.toptex.io/v3/products?"
            "catalog_reference=ns300&usage_right=b2b_uniquement"
        )
        headers = {
            "x-api-key": self._get_toptex_credential('toptex_api_key'),
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        response = requests.get(
            proxy_url,
            params={"url": product_url},
            headers=headers,
        )
        if response.status_code != 200:
            raise UserError(f"Error al obtener datos de producto TopTex: {response.text}")

        result = response.json()
        if not result or not isinstance(result, list):
            raise UserError("Respuesta inválida o vacía de TopTex")

        for product in result:
            name = product.get("label")
            reference = product.get("catalogReference")
            if name and reference:
                existing = self.env['product.template'].search([('default_code', '=', reference)])
                if not existing:
                    self.env['product.template'].create({
                        'name': name,
                        'default_code': reference,
                        'type': 'product',
                        'toptex_id': product.get("productReference", ""),
                    })