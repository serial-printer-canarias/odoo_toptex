import requests
from odoo import models, fields
from odoo.exceptions import UserError


class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado desde TopTex'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema no encontrado: {key}")
        return param

    def _generate_token(self):
        proxy_url = self._get_toptex_credential("toptex_proxy_url")
        token_url = "https://api.toptex.com/v3/oauth/token"

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "Accept": "application/json",
            "Accept-Encoding": "identity",  # Para evitar errores de gzip
        }

        data = {
            "username": self._get_toptex_credential("toptex_username"),
            "password": self._get_toptex_credential("toptex_password"),
        }

        response = requests.post(
            proxy_url,
            params={"url": token_url},
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            return response.json().get("token")
        else:
            raise UserError(f"Error al generar token: {response.text}")

    def sync_products_from_api(self):
        proxy_url = self._get_toptex_credential("toptex_proxy_url")
        catalog_url = (
            "https://api.toptex.com/v3/products/all"
            "?usage_right=b2b_uniquement&result_in_file=1"
        )
        token = self._generate_token()

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",  # Para evitar gzip
        }

        response = requests.get(
            proxy_url,
            params={"url": catalog_url},
            headers=headers,
        )

        if response.status_code == 200:
            catalog = response.json()
            for product_data in catalog.get("items", []):
                self._create_or_update_product(product_data)
        else:
            raise UserError(f"Error al obtener catálogo: {response.text}")

    def _create_or_update_product(self, product_data):
        toptex_id = product_data.get("id")
        name = product_data.get("label")

        product = self.search([("toptex_id", "=", toptex_id)], limit=1)
        if product:
            product.write({"name": name})
        else:
            self.create({"name": name, "toptex_id": toptex_id})