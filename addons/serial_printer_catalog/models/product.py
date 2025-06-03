import requests
import logging
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("Faltan parámetros del sistema para autenticar contra la API de TopTex.")

        # Paso 1: Generar token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando en TopTex: {auth_response.text}")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió un token válido de TopTex.")

        # Paso 2: Obtener el producto por SKU
        sku = "NS300.68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            raise UserError(f"Error al obtener el producto: {response.text}")

        try:
            data = response.json()
        except Exception:
            raise UserError("No se pudo convertir la respuesta en JSON.")

        # Logs de depuración
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", data)

        # Interpretar estructura de respuesta
        if isinstance(data, dict):
            productos = [data]
        elif isinstance(data, list):
            productos = data
        elif "products" in data:
            productos = data["products"]
        else:
            raise UserError("La API devolvió una lista vacía o mal estructurada.")

        for item in productos:
            name = item.get("translatedName", {}).get("es") or item.get("translatedName", {}).get("en")
            sku = item.get("sku")
            price = item.get("publicPrice", 0.0)

            if not name or not sku:
                _logger.warning("Producto ignorado por falta de campos obligatorios: %s", item)
                continue

            self.env["product.template"].create({
                "name": name,
                "default_code": sku,
                "list_price": price,
                "type": "product",
                "sale_ok": True,
                "purchase_ok": True,
            })