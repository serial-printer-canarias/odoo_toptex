import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado de TopTex'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    reference = fields.Char(string='Referencia')
    price = fields.Float(string='Precio')

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Falta el parámetro de configuración: {key}")
        return param

    def _generate_token(self):
        # URL del proxy y llamada a autenticación
        proxy_url = 'https://toptex-proxy.onrender.com/proxy'
        auth_url = 'https://api.toptex.io/v3/authenticate'

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "Accept": "application/json"
        }

        data = {
            "username": self._get_toptex_credential("toptex_username"),
            "password": self._get_toptex_credential("toptex_password")
        }

        response = requests.post(proxy_url, params={"url": auth_url}, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("token")
        else:
            raise UserError(f"❌ Error generando token: {response.status_code} → {response.text}")

    @api.model
    def sync_products_from_api(self):
        token = self._generate_token()

        # URL para obtener todos los productos
        product_url = "https://api.toptex.io/v3/products?usage_right=b2b_uniquement&result_in_file=1"
        proxy_url = "https://toptex-proxy.onrender.com/proxy"

        headers = {
            "x-api-key": self._get_toptex_credential("toptex_api_key"),
            "x-toptex-authorization": token,
            "Accept-Encoding": "identity",  # Evita gzip para no fallar en Odoo.sh
            "Accept": "application/json"
        }

        response = requests.get(proxy_url, params={"url": product_url}, headers=headers)

        if response.status_code == 200:
            productos = response.json().get("products", [])
            if not productos:
                raise UserError("✅ Conexión exitosa, pero sin productos.")
            for p in productos:
                if not p.get("sku"):
                    continue  # ignorar si no hay SKU
                self.create({
                    "name": p.get("label"),
                    "toptex_id": p.get("id"),
                    "reference": p.get("sku"),
                    "price": p.get("price", 0.0),
                })
        else:
            raise UserError(f"❌ Error al obtener productos: {response.status_code} → {response.text}")