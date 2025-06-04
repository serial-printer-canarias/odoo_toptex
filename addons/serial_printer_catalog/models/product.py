import json
import logging
import requests
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        _logger.info("🔁 Iniciando sincronización con la API de TopTex...")

        # Crear producto de prueba
        try:
            test_product = self.env['product.template'].create({
                'name': 'Producto de Prueba',
                'default_code': 'PRUEBA123',
                'list_price': 12.34,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })
            _logger.info("✅ Producto de prueba creado correctamente: %s", test_product.name)
        except Exception as e:
            _logger.error("❌ Error al crear producto de prueba: %s", str(e))

        # Obtener parámetros
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales en los parámetros del sistema")
            return

        # Paso 1: Obtener el token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json().get("token")
            if not token:
                _logger.error("❌ No se recibió token de autenticación")
                return
            _logger.info("🔐 Token obtenido correctamente")
        except Exception as e:
            _logger.error("❌ Error al autenticar con TopTex: %s", str(e))
            return

        # Paso 2: Obtener datos del producto
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "toptex-authorization": token,
            "api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            product_data = response.json()
            _logger.info("📦 JSON recibido de la API de TopTex: %s", json.dumps(product_data, indent=2))
        except Exception as e:
            _logger.error("❌ Error al obtener el producto desde TopTex: %s", str(e))
            return

        if not isinstance(product_data, dict):
            _logger.error("❌ Formato inesperado en la respuesta de la API: %s", type(product_data))
            return

        # Paso 3: Mapear datos de TopTex a Odoo
        try:
            name = product_data.get("designation", {}).get("es", "Producto sin nombre")
            default_code = product_data.get("supplierReference", "")
            description = product_data.get("description", {}).get("es", "")
            list_price_raw = product_data.get("colors", [])[0].get("sizes", [])[0].get("publicUnitPrice", "")
            list_price = float(list_price_raw.replace("€", "").replace(",", ".").strip()) if list_price_raw else 0.0
            image_url = product_data.get("images", [])[0].get("url_image", "")

            new_product = self.env['product.template'].create({
                'name': name,
                'default_code': default_code,
                'list_price': list_price,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
                'description': description,
                'image_1920': requests.get(image_url).content if image_url else False,
            })

            _logger.info("✅ Producto NS300 creado correctamente: %s", new_product.name)

        except Exception as e:
            _logger.error("❌ Error al crear producto NS300 en Odoo: %s", str(e))