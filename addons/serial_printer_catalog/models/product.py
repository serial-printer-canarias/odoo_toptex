import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto de TopTex importado'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID TopTex", index=True)

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no encontrado.")
        return param

    def _generate_token(self):
        url = self._get_toptex_credential('toptex_proxy_url')
        target = "https://api.toptex.com/v2/oauth/token"

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "Content-Type": "application/json"
        }
        data = {
            "username": self._get_toptex_credential("toptex_username"),
            "password": self._get_toptex_credential("toptex_password")
        }

        response = requests.post(
            url,
            params={"url": target},
            json=data,
            headers=headers
        )

        if response.status_code == 200:
            return response.json().get("token")
        else:
            raise UserError(f"Error al generar token ({response.status_code}): {response.text}")

    @api.model
    def sync_products_from_api(self):
        proxy_url = self._get_toptex_credential("toptex_proxy_url")
        catalog_url = "https://api.toptex.com/v3/products/all?usage_right=b2b_uniquement&result_in_file=1"
        token = self._generate_token()

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "x-toptex-authorization": token,
            "Accept": "application/json",
            "Accept-Encoding": "identity"
        }

        response = requests.get(
            proxy_url,
            params={"url": catalog_url},
            headers=headers
        )

        if response.status_code == 200:
            catalog = response.json()
            for product_data in catalog.get("items", []):
                self._create_or_update_product(product_data)
        else:
            raise UserError(f"Error al obtener catálogo ({response.status_code}): {response.text}")

    def _create_or_update_product(self, product_data):
        toptex_id = product_data.get("id")
        name = product_data.get("name", {}).get("default", "Sin nombre")

        product = self.search([("toptex_id", "=", toptex_id)], limit=1)
        if product:
            product.write({"name": name})
        else:
            self.create({
                "toptex_id": toptex_id,
                "name": name
            })