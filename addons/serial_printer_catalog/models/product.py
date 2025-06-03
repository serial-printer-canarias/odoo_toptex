import json
import requests
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros de configuración en el sistema.")

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_data)
        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")
        
        token = auth_response.json().get("token")
        if not token:
            raise UserError("Token no recibido desde la API.")

        # Petición de producto individual por SKU
        sku = "NS300.68558_68494"  # SKU exacto a buscar
        catalog_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)

        if response.status_code != 200:
            raise UserError("Error al obtener datos del producto.")

        try:
            data = response.json()
        except Exception:
            raise UserError("No se pudo convertir la respuesta en JSON.")

        # Logs de depuración
        _logger.info("Tipo de dato devuelto por la API: %s", type(data))
        _logger.info("Contenido recibido: %s", json.dumps(data, indent=2, ensure_ascii=False))

        # Interpretación robusta de la respuesta
        if isinstance(data, dict):
            if "products" in data:
                productos = data["products"]
            else:
                productos = [data]
        elif isinstance(data, list):
            productos = data
        else:
            raise UserError("Respuesta inesperada de la API de TopTex (no es un dict ni lista).")

        if not productos:
            raise UserError("La API devolvió una lista vacía.")

        for product in productos:
            catalog_ref = product.get("catalogReference")
            if not catalog_ref:
                continue

            existing = self.env['product.template'].search([('default_code', '=', catalog_ref)], limit=1)
            if existing:
                _logger.info("Producto ya existe en Odoo: %s", catalog_ref)
                continue

            name = product.get("designation", {}).get("fr") or catalog_ref
            description = product.get("description", {}).get("fr", "")
            new_product = self.env['product.template'].create({
                'name': name,
                'default_code': catalog_ref,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
                'description': description,
            })

            _logger.info("Producto creado: %s (ID %s)", new_product.name, new_product.id)