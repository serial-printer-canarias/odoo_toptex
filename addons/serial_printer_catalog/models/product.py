import base64
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()

        username = IrConfigParam.get_param('toptex_username')
        password = IrConfigParam.get_param('toptex_password')
        api_key = IrConfigParam.get_param('toptex_api_key')
        proxy_url = IrConfigParam.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("Faltan parámetros de configuración para TopTex.")
            return

        # Paso 1: obtener el token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
        }
        auth_payload = {
            'username': username,
            'password': password
        }

        try:
            auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
            _logger.info(f"Token obtenido correctamente: {token}")
        except Exception as e:
            _logger.error(f"Error al obtener el token: {e}")
            return

        # Paso 2: llamar a la API del producto
        catalog_reference = 'NS300'
        product_url = f"{proxy_url}/v3/products/{catalog_reference}?usage_right=b2b_b2c"
        product_headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'toptex-authorization': token,
            'Accept-Encoding': 'gzip',
        }

        try:
            product_response = requests.get(product_url, headers=product_headers)
            product_response.raise_for_status()
            product_json = product_response.json()
            _logger.info("Respuesta JSON del producto recibida correctamente.")
        except Exception as e:
            _logger.error(f"Error al obtener el producto: {e}")
            return

        # Paso 3: parsear y mapear los datos
        try:
            catalog_reference = product_json.get('catalogReference')
            translated_name = product_json.get('translatedName', {})
            name = translated_name.get('es') or translated_name.get('en') or catalog_reference
            brand = product_json.get('brand', {}).get('name', 'Desconocida')
            description = product_json.get('description', {}).get('es') or ''
            default_code = catalog_reference

            image_url = ''
            colors = product_json.get('colors', [])
            if colors:
                image_url = colors[0].get('media', {}).get('images', [{}])[0].get('url', '')

            image_1920 = False
            if image_url:
                try:
                    image_response = requests.get(image_url)
                    image_response.raise_for_status()
                    image = Image.open(BytesIO(image_response.content))
                    buffer = BytesIO()
                    image.save(buffer, format='PNG')
                    image_1920 = base64.b64encode(buffer.getvalue())
                except Exception as img_error:
                    _logger.warning(f"No se pudo procesar la imagen: {img_error}")

            # Precio y stock ficticios por ahora
            list_price = 10.0
            standard_price = 5.0
            stock_qty = 100

            product_vals = {
                'name': name,
                'default_code': default_code,
                'type': 'consu',
                'list_price': list_price,
                'standard_price': standard_price,
                'description_sale': description,
                'image_1920': image_1920,
            }

            existing_product = self.env['product.template'].sudo().search([('default_code', '=', default_code)], limit=1)
            if existing_product:
                _logger.info(f"Producto ya existe: {default_code}")
                existing_product.write(product_vals)
            else:
                created_product = self.env['product.template'].sudo().create(product_vals)
                _logger.info(f"Producto creado: {created_product.name}")
        except Exception as e:
            _logger.error(f"Error al procesar el producto: {e}")