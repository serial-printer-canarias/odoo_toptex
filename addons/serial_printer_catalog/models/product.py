# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from odoo import models, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        params = self.env['ir.config_parameter'].sudo()
        username = params.get_param('toptex_username')
        password = params.get_param('toptex_password')
        api_key = params.get_param('toptex_api_key')
        proxy_url = params.get_param('toptex_proxy_url')

        sku = 'NS300.68558_68494'

        # Paso 1: AUTENTICACIÓN – Payload primero, luego headers
        auth_url = f"{proxy_url}/v3/authenticate"
        payload = {
            "login": username,
            "password": password
        }
        headers_auth = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, headers=headers_auth, json=payload)
        if auth_response.status_code != 200:
            _logger.error("❌ No se pudo obtener el token de autenticación")
            return

        token = auth_response.json().get("token")
        if not token:
            _logger.error("❌ Token vacío en respuesta")
            return

        # Paso 2: PETICIÓN DEL PRODUCTO (con token correcto)
        product_url = f"{proxy_url}/v3/products/sku/{sku}?usage_right=b2b_uniquement"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"❌ Error al obtener producto: {response.text}")
            return

        product_data = response.json()
        _logger.info(f"✅ JSON recibido:\n{json.dumps(product_data, indent=2)}")

        # Paso 3: MAPEAR datos TopTex → Odoo
        name = product_data.get("translatedName", {}).get("es", "Sin nombre")
        default_code = product_data.get("catalogReference", "Sin referencia")
        description = product_data.get("description", "")
        brand = product_data.get("brand", {}).get("name", "Sin marca")
        list_price = product_data.get("publicPrice", 0.0)
        standard_price = product_data.get("purchasePrice", 0.0)

        # Paso 4: Imagen
        def get_image_from_url(image_url):
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(image_url, headers=headers)
                if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                    return base64.b64encode(response.content)
            except Exception as e:
                _logger.error(f"❌ Error descargando imagen: {e}")
            return False

        image_url = ""
        try:
            color_data = product_data.get("colors", [])[0]
            image_url = color_data.get("images", [])[0].get("url", "")
        except Exception as e:
            _logger.warning(f"⚠️ No se pudo extraer imagen principal: {e}")

        image_data = get_image_from_url(image_url)

        # Paso 5: Crear producto
        self.create({
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'image_1920': image_data,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        _logger.info("✅ Producto creado correctamente con nombre, marca, descripción, precios e imagen.")