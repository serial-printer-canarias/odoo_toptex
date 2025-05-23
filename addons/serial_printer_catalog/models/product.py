import requests
from datetime import datetime, timedelta
import pytz
from odoo import models, fields, api

class SerialPrinterProduct(models.Model):
    _name = "serial.printer.product"
    _description = "Producto de Catálogo"

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID TopTex")
    description = fields.Text(string="Descripción")
    price = fields.Float(string="Precio")
    image_url = fields.Char(string="URL Imagen")

    _token = None
    _token_expiry = None

    def get_api_token(self):
        """Renueva el token si ha caducado"""
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)
        if self._token and self._token_expiry and now < self._token_expiry:
            return self._token

        api_key = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        username = "toes_bafaluydelreymarc"
        password = "Bafarey12345."
        url = "https://api.toptex.io/v3/authenticate"

        headers = {
            "x-api-key": api_key,
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        data = {
            "username": username,
            "password": password
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            token_data = response.json()
            self._token = token_data.get("token")
            expires_in = token_data.get("expires_in", 3600)
            self._token_expiry = now + timedelta(seconds=expires_in)
            return self._token
        else:
            raise Exception(f"Error al obtener token: {response.status_code} {response.text}")

    def sync_products_from_api(self):
        token = self.get_api_token()
        url = "https://api.toptex.io/v3/products"
        headers = {
            "Authorization": f"Bearer {token}",
            "accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products_data = response.json().get("items", [])
            for product in products_data:
                self.env["serial.printer.product"].create({
                    "name": product.get("name"),
                    "toptex_id": product.get("id"),
                    "description": product.get("description", ""),
                    "price": product.get("price", 0.0),
                    "image_url": product.get("image", {}).get("src", "")
                })
        else:
            raise Exception(f"Error al sincronizar productos: {response.status_code} {response.text}")