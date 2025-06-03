import requests
import logging
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_param('toptex_api_key')
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan credenciales en los parámetros del sistema.")

        # Paso 1: Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)

        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token de autenticación.")

        # Paso 2: Llamada al producto NS300
        catalog_url = f"{proxy_url}/v3/products?sku=NS300-68558_68494&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError("No se pudo recuperar el catálogo desde la API de TopTex.")

        data = response.json()

        # DEPURACIÓN: Ver estructura real de la respuesta
        _logger.warning("📦 Respuesta completa de TopTex (JSON): %s", data)

        if not isinstance(data, dict):
            raise UserError("Respuesta inesperada de la API de TopTex (no es un dict).")

        # Buscar producto NS300 dentro del dict
        productos = data.get("products") or data.get("data") or data.get("result") or []

        if not isinstance(productos, list):
            raise UserError("Respuesta inesperada de la API de TopTex (no es una lista).")

        productos_ns300 = [p for p in productos if p.get('catalogReference') == 'NS300']
        if not productos_ns300:
            raise UserError("No se encontró el producto NS300 en la respuesta.")

        producto = productos_ns300[0]
        nombre = producto.get("name") or producto.get("product_name") or "NS300"
        descripcion = producto.get("description", "")
        referencia = producto.get("catalogReference", "NS300")

        # Crear product.template
        self.create({
            "name": nombre,
            "default_code": referencia,
            "type": "product",
            "description_sale": descripcion,
        })