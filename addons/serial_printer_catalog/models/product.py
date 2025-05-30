# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError
import requests

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Sincronizador de productos TopTex'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID TopTex")

    def _get_toptex_credential(self, key):
        param = self.env['ir.config_parameter'].sudo().get_param(key)
        if not param:
            raise UserError(f"Parámetro del sistema '{key}' no configurado")
        return param

    def _generate_token(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token_url = 'https://api.toptex.io/v3/authenticate'
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
        else:
            raise UserError(f"Error al generar token TopTex: {response.text}")

    def sync_toptex_product(self):
        proxy_url = self._get_toptex_credential('toptex_proxy_url')
        token = self._generate_token()

        product_url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
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
            raise UserError(f"Error al obtener producto: {response.text}")

        result = response.json()
        items = result.get("items", [])

        if not items:
            raise UserError("No se recibió ningún producto del API")

        for item in items:
            values = {
                "name": item.get("name", "Producto TopTex"),
                "default_code": item.get("reference", ""),
                "list_price": item.get("price", 0.0),
                "type": "product",
            }

            # Verificar categoría si está disponible
            categ_name = item.get("category")
            if categ_name:
                categ = self.env["product.category"].search([("name", "=", categ_name)], limit=1)
                if not categ:
                    categ = self.env["product.category"].create({"name": categ_name})
                values["categ_id"] = categ.id

            # Crear producto
            self.env["product.template"].create(values)