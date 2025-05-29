import json
import requests
from odoo import models, fields
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Char("TopTex ID")

class ProductImporter(models.Model):
    _name = 'serial_printer.product_importer'
    _description = 'Importador de productos TopTex'

    def _get_toptex_credentials(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            raise UserError("Falta algún parámetro de configuración (proxy_url, username, password, api_key).")

        return proxy_url, username, password, api_key

    def _generate_token(self):
        proxy_url, username, password, api_key = self._get_toptex_credentials()
        auth_url = "https://api.toptex.com/v3/token"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        }
        data = {"username": username, "password": password}

        response = requests.post(
            proxy_url,
            params={"url": auth_url},
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise UserError(f"Error al obtener token: {response.status_code} - {response.text}")

        return response.json().get("token")

    def _fetch_all_products(self, token):
        proxy_url, _, _, api_key = self._get_toptex_credentials()
        products_url = "https://api.toptex.com/v3/products?usage_right=b2b_uniquement&result_in_file=1"

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        }

        response = requests.get(
            proxy_url,
            params={"url": products_url},
            headers=headers
        )

        if response.status_code != 200:
            raise UserError(f"Error al obtener productos: {response.status_code} - {response.text}")

        return response.json().get("items", [])

    def sync_products_from_api(self):
        token = self._generate_token()
        products = self._fetch_all_products(token)

        for product in products:
            ref = product.get("sku")
            name = product.get("label")
            if not ref or not name:
                continue

            existing = self.env['product.template'].search([('default_code', '=', ref)], limit=1)
            if existing:
                existing.write({
                    'name': name,
                })
            else:
                self.env['product.template'].create({
                    'name': name,
                    'default_code': ref,
                    'type': 'product',
                    'toptex_id': str(product.get("id")),
                })