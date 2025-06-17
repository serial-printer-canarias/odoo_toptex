import requests
import base64
import logging
from io import BytesIO
from PIL import Image
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # 1. Recuperar parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            _logger.error("Faltan parámetros del sistema.")
            return

        # 2. Obtener token desde el proxy
        token_url = f'{proxy_url}/v3/authenticate'
        headers_auth = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
        }
        payload = {
            'username': username,
            'password': password
        }

        token_response = requests.post(token_url, headers=headers_auth, json=payload)
        _logger.info(f"Token status: {token_response.status_code}")
        if token_response.status_code != 200:
            _logger.error("Error al autenticar contra TopTex.")
            return

        token = token_response.json().get('token')
        if not token:
            _logger.error("Token vacío o no recibido.")
            return

        # 3. Llamada al producto por catalogReference
        catalog_reference = 'NS300'
        product_url = f'{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c'
        headers_data = {
            'toptex-authorization': token,
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        response = requests.get(product_url, headers=headers_data)
        _logger.info(f"Status producto: {response.status_code}")
        _logger.debug(f"Respuesta cruda JSON: {response.text}")

        if response.status_code != 200:
            _logger.error("Error al obtener datos del producto.")
            return

        json_data = response.json()
        if isinstance(json_data, list):
            product_data = json_data[0] if json_data else {}
        elif isinstance(json_data, dict):
            product_data = json_data
        else:
            _logger.error("Formato de JSON no reconocido.")
            return

        if not product_data:
            _logger.warning("No se encontró información del producto.")
            return

        # 4. Parsear datos principales
        name = product_data.get('translatedName', {}).get('es', 'Producto sin nombre')
        default_code = product_data.get('catalogReference')
        brand_name = product_data.get('brand', {}).get('name', '')
        description = product_data.get('description', {}).get('es', '')
        main_image_url = product_data.get('images', {}).get('main')

        # 5. Obtener o crear marca
        brand = self.env['product.brand'].sudo().search([('name', '=', brand_name)], limit=1)
        if not brand:
            brand = self.env['product.brand'].sudo().create({'name': brand_name})

        # 6. Crear categoría genérica si no existe
        categ = self.env['product.category'].search([('name', '=', 'All Products')], limit=1)
        if not categ:
            categ = self.env['product.category'].create({'name': 'All Products'})

        # 7. Procesar imagen principal
        image_1920 = False
        if main_image_url:
            try:
                img_response = requests.get(main_image_url)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    buffer = BytesIO()
                    image.save(buffer, format='PNG')
                    image_1920 = base64.b64encode(buffer.getvalue())
            except Exception as e:
                _logger.error(f"Error procesando imagen: {str(e)}")

        # 8. Crear producto principal (template)
        product_template = self.env['product.template'].sudo().create({
            'name': name,
            'default_code': default_code,
            'description_sale': description,
            'image_1920': image_1920,
            'categ_id': categ.id,
            'type': 'consu',
            'standard_price': 0.0,
            'list_price': 0.0,
            'product_brand_id': brand.id,
        })

        # 9. Atributos y variantes
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        variant_lines = []
        colors = product_data.get('colors', [])
        for color in colors:
            color_name = color.get('translatedName', {}).get('es')
            if not color_name:
                continue
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })

            sizes = color.get('sizes', [])
            for size in sizes:
                size_label = size.get('label')
                if not size_label:
                    continue
                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_label), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({
                        'name': size_label,
                        'attribute_id': size_attr.id
                    })

                variant_lines.append((0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [color_value.id])]
                }))
                variant_lines.append((0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [size_value.id])]
                }))

        if variant_lines:
            product_template.write({'attribute_line_ids': variant_lines})

        _logger.info(f"Producto {default_code} sincronizado correctamente con variantes.")