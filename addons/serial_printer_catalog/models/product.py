import requests
import json
import base64
import logging
from PIL import Image
from io import BytesIO
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        # Generar Token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            _logger.error(f"Error al autenticar: {auth_response.status_code} - {auth_response.text}")
            return

        token = auth_response.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        # Descargar producto por catalog_reference
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products/{catalog_reference}?usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"Error en llamada a producto: {response.status_code}")
            return

        # Parseo robusto
        try:
            full_response = response.json()
            _logger.info("📦 JSON principal recibido:")
            _logger.info(json.dumps(full_response, indent=2))

            # Manejo dict vs list
            if isinstance(full_response, list):
                if len(full_response) > 0:
                    data = full_response[0]
                else:
                    _logger.error("❌ Lista vacía en respuesta.")
                    return
            elif isinstance(full_response, dict):
                if full_response:
                    data = full_response
                else:
                    _logger.error("❌ No se encontraron datos dentro del dict.")
                    return
            else:
                _logger.error("❌ Respuesta inesperada de formato JSON.")
                return

        except Exception as e:
            _logger.error(f"Error interpretando JSON: {str(e)}")
            return

        # Mapeo de datos básico
        name = data.get("designation", {}).get("es", "Sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", catalog_reference)

        # Marca segura
        brand_data = data.get("brand", {})
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", {}).get("es", "Sin Marca")
        else:
            brand = "Sin Marca"

        _logger.info(f"Creando producto: {name} [{default_code}] Marca: {brand}")

        # Imagen principal
        image_url = None
        images = data.get("images", [])
        if images:
            first_image = images[0]
            image_url = first_image.get("url")

        image_data = None
        if image_url:
            try:
                image_response = requests.get(image_url)
                if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                    img = Image.open(BytesIO(image_response.content))
                    img_buffer = BytesIO()
                    img.save(img_buffer, format='PNG')
                    image_data = base64.b64encode(img_buffer.getvalue())
                else:
                    _logger.warning("⚠️ Imagen no válida o no encontrada.")
            except Exception as e:
                _logger.warning(f"⚠️ Error procesando imagen: {str(e)}")

        # Crear o actualizar producto
        product_vals = {
            'name': name,
            'default_code': default_code,
            'description_sale': description,
            'type': 'consu',
            'categ_id': self.env.ref('product.product_category_all').id,
            'standard_price': 0.0,
            'list_price': 0.0,
            'image_1920': image_data,
        }

        product = self.env['product.template'].create(product_vals)
        _logger.info("✅ Producto creado correctamente.")

        _logger.info("✅ Sincronización inicial terminada correctamente.")