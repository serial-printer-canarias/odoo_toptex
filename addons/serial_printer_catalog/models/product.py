import json
import base64
import requests
from io import BytesIO
from PIL import Image
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')
        proxy_url = IrConfig.get_param('toptex_proxy_url')

        # Obtener token desde proxy
        auth_url = f'{proxy_url}/v3/authenticate'
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}

        try:
            auth_response = requests.post(auth_url, headers=headers, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
            if not token:
                _logger.error('No se pudo obtener token de autenticación')
                return
            _logger.info('Token recibido correctamente.')
        except Exception as e:
            _logger.error(f'Error autenticando: {e}')
            return

        # Llamada de producto individual con URL correcta
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        product_headers = {
            'x-api-key': api_key,
            'toptex-authorization': token,
            'Content-Type': 'application/json'
        }

        try:
            product_response = requests.get(product_url, headers=product_headers)
            product_response.raise_for_status()
            product_data = product_response.json()
            _logger.info(f"JSON completo recibido: {json.dumps(product_data)}")
        except Exception as e:
            _logger.error(f"Error al obtener datos del producto: {e}")
            return

        # Parsing robusto dict o list
        if isinstance(product_data, list):
            products = product_data
        elif isinstance(product_data, dict):
            products = [product_data]
        else:
            _logger.error("Formato de datos no reconocido")
            return

        for product in products:
            name = product.get("translatedName", {}).get("es", "SIN NOMBRE")
            default_code = product.get("catalogReference", "SIN_REF")
            description = product.get("description", {}).get("es", "")
            brand_data = product.get("brand", {})
            brand_name = brand_data.get("name", {}).get("es", "Sin Marca")

            _logger.info(f"Procesando producto: {default_code} - {name} - Marca: {brand_name}")

            # De momento sólo creamos el producto básico (sin variantes ni imágenes de variantes)
            product_template = self.env['product.template'].create({
                'name': name,
                'default_code': default_code,
                'description_sale': description,
                'type': 'product',
                'list_price': 0.0,
                'standard_price': 0.0,
            })

            _logger.info(f"Producto creado: {product_template.name}")

            # Imagen principal si existe
            image_url = ""
            if product.get("images"):
                image_url = product.get("images")[0].get("url", "")
            if image_url:
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        img = Image.open(BytesIO(image_response.content))
                        img = img.convert('RGB')
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        product_template.image_1920 = base64.b64encode(img_byte_arr.getvalue())
                        _logger.info("Imagen principal descargada correctamente")
                except Exception as e:
                    _logger.warning(f"No se pudo cargar la imagen principal: {e}")

        _logger.info("Proceso de sincronización terminado correctamente.")