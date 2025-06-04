import json
import logging
import requests
import base64
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        _logger.info("🔄 Iniciando sincronización con la API de TopTex...")

        # Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales en los parámetros del sistema.")
            return

        # Crear producto de prueba estático
        self.env['product.template'].create({
            'name': 'Producto de prueba',
            'default_code': 'PRUEBA123',
            'list_price': 1.00,
            'type': 'product',
            'uom_id': 1,
            'uom_po_id': 1,
        })
        _logger.info("✅ Producto de prueba creado correctamente.")

        # Paso 1: Obtener token
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
            _logger.info(f"🔑 Token recibido: {token}")
        except Exception as e:
            _logger.error(f"❌ Error al autenticar con TopTex: {str(e)}")
            return

        # Paso 2: Obtener el producto NS300_68558_68494
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "Content-Type": "application/json",
            "toptex-authorization": token
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            _logger.info(f"📦 Contenido recibido desde TopTex: {json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener el producto desde TopTex: {str(e)}")
            return

        # Validar que el JSON no esté vacío
        if not data or isinstance(data, list) and len(data) == 0:
            _logger.warning("⚠️ El JSON recibido está vacío o mal formado.")
            return

        # Paso 3: Mapear y crear producto NS300
        try:
            product_name = data.get("designation", {}).get("es", "Sin nombre")
            product_code = data.get("supplierReference", sku)
            product_price = 8.60  # Valor ficticio, ajustar si se desea extraer real

            image_url = data.get("images", [])[0].get("url_image") if data.get("images") else None
            image_base64 = None
            if image_url:
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    image_base64 = base64.b64encode(img_response.content).decode("utf-8")

            self.env['product.template'].create({
                'name': product_name,
                'default_code': product_code,
                'list_price': product_price,
                'type': 'product',
                'uom_id': 1,
                'uom_po_id': 1,
                'image_1920': image_base64,
            })

            _logger.info(f"✅ Producto {product_code} creado correctamente en Odoo.")
        except Exception as e:
            _logger.error(f"❌ Error al crear el producto NS300: {str(e)}")