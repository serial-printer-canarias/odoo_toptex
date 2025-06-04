import requests
import json
import logging
from odoo import models, fields, api, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')

        if not all([username, password, api_key]):
            raise UserError("Faltan parámetros del sistema: username, password o api_key.")

        # 1. Obtener token
        auth_url = 'https://api.toptex.io/v3/authenticate'
        auth_data = {
            'username': username,
            'password': password,
            'apiKey': api_key
        }
        auth_headers = {'Content-Type': 'application/json'}
        auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)

        if auth_response.status_code != 200:
            raise UserError(f"Error de autenticación: {auth_response.status_code} - {auth_response.text}")

        token = auth_response.json().get('token')
        if not token:
            raise UserError("No se recibió token desde la API.")

        # 2. Llamar a la API del producto
        sku = 'NS300_68558_68494'
        product_url = f'https://api.toptex.com/v3/products/{sku}?usage_right=b2b_uniquement'
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept-Encoding': 'gzip, deflate, br',
        }

        _logger.info(f"Solicitando producto a URL: {product_url}")
        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            raise UserError(f"Error al obtener producto: {response.status_code} - {response.text}")

        try:
            product_data = response.json()
        except Exception as e:
            raise UserError(f"No se pudo interpretar JSON: {e}")

        _logger.info(f"Contenido recibido de la API: {json.dumps(product_data, indent=2)}")

        # 3. Validar que hay contenido
        if not isinstance(product_data, dict) or not product_data.get('catalogReference'):
            raise UserError("Respuesta vacía o sin datos válidos del producto.")

        name = product_data['designation']['es'] or product_data['designation']['en']
        description = product_data['description']['es'] or product_data['description']['en']
        default_code = sku
        list_price = float(product_data.get('colors', [{}])[0].get('sizes', [{}])[0].get('publicUnitPrice', '0').replace('€', '').replace(',', '.').strip() or 0)

        # Crear producto si no existe
        existing = self.env['product.template'].search([('default_code', '=', default_code)])
        if existing:
            _logger.info(f"El producto {default_code} ya existe.")
            return

        # Crear el producto base
        product_vals = {
            'name': name,
            'default_code': default_code,
            'list_price': list_price,
            'type': 'product',
            'description_sale': description,
        }

        product = self.create(product_vals)

        # 4. Subir imagen principal
        try:
            image_url = product_data['images'][0]['url_image']
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                product.image_1920 = image_response.content
                _logger.info(f"Imagen añadida desde {image_url}")
        except Exception as e:
            _logger.warning(f"No se pudo obtener imagen: {e}")

        _logger.info(f"Producto {name} creado correctamente desde API TopTex.")