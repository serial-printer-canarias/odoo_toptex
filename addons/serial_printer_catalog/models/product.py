import requests
import json
import base64
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Recuperar los parámetros desde ir.config_parameter
        config = self.env['ir.config_parameter'].sudo()
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        api_key = config.get_param('toptex_api_key')
        proxy_url = config.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan parámetros de configuración en el sistema.")
            return

        # 1️⃣ Autenticación: Obtener el token
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        auth_payload = {
            'username': username,
            'password': password
        }

        try:
            auth_response = requests.post(auth_url, headers=headers, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
            if not token:
                _logger.error("❌ No se pudo obtener el token de autenticación.")
                return
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error durante autenticación: {str(e)}")
            return

        # 2️⃣ Obtener datos del producto por catalog_reference
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"

        product_headers = {
            'Authorization': token,
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        _logger.info(f"🔎 URL de producto: {product_url}")
        _logger.info(f"🔎 Headers de producto: {product_headers}")

        try:
            product_response = requests.get(product_url, headers=product_headers)
            if product_response.status_code != 200:
                _logger.error(f"❌ Error en llamada de producto: {product_response.status_code}")
                return

            product_data = product_response.json()
            _logger.info(f"📦 JSON principal recibido: {json.dumps(product_data)}")

        except Exception as e:
            _logger.error(f"❌ Error al obtener datos de producto: {str(e)}")
            return

        # Validación del dict (puede ser lista o dict)
        if isinstance(product_data, list):
            if not product_data:
                _logger.error("❌ No se encontró producto en la respuesta.")
                return
            product_data = product_data[0]
        elif not isinstance(product_data, dict):
            _logger.error("❌ Formato de respuesta inesperado.")
            return

        # 3️⃣ Mapping de datos
        name = product_data.get("translatedName", {}).get("es", "SIN NOMBRE")
        default_code = product_data.get("catalogReference", "SIN_REF")

        categ = self.env['product.category'].search([('name', '=', 'TopTex')], limit=1)
        if not categ:
            categ = self.env['product.category'].create({'name': 'TopTex'})

        # Crear el producto
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'categ_id': categ.id,
            'sale_ok': True,
            'purchase_ok': True,
        }

        product_template = self.env['product.template'].create(template_vals)
        _logger.info(f"✅ Producto creado: {name}")
        _logger.info("✅ Sincronización inicial terminada correctamente.")