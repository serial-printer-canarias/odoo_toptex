import json
import logging
import requests
from odoo import models, fields

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer los parámetros desde el sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        # Obtener token
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_payload = {'username': username, 'password': password}
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        response = requests.post(auth_url, headers=headers, json=auth_payload)
        token = response.json().get('token')
        if not token:
            _logger.error('No se pudo obtener el token de autenticación')
            return

        _logger.info('✅ Token recibido correctamente.')

        # Solicitar el producto por catalog_reference
        catalog_reference = 'NS300'
        product_url = f'{proxy_url}/v3/products/{catalog_reference}?usage_right=b2b_b2c'
        product_headers = {
            'x-api-key': api_key,
            'toptex-authorization': token,
            'Content-Type': 'application/json'
        }

        product_response = requests.get(product_url, headers=product_headers)
        if product_response.status_code != 200:
            _logger.error(f'Error en llamada de producto: {product_response.status_code}')
            return

        product_data = product_response.json()
        _logger.info(f'JSON principal recibido: {json.dumps(product_data, indent=4)}')

        # Validar datos principales
        product_name = product_data.get("translatedName", {}).get("es", "Producto sin nombre")
        reference = product_data.get("catalogReference", "SIN_REF")

        # Crear la categoría por defecto
        category = self.env['product.category'].search([('name', '=', 'All')], limit=1)

        # Crear atributos si no existen
        color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attribute:
            color_attribute = self.env['product.attribute'].create({'name': 'Color'})

        size_attribute = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attribute:
            size_attribute = self.env['product.attribute'].create({'name': 'Talla'})

        # Crear product.template
        template = self.create({
            'name': product_name,
            'default_code': reference,
            'type': 'consu',
            'categ_id': category.id,
            'sale_ok': True,
            'purchase_ok': True,
            'attribute_line_ids': []
        })

        # Procesar variantes
        attribute_lines = []

        # Colores
        color_values = []
        for color in product_data.get('colors', []):
            color_name = color.get('translatedColorName', {}).get('es', color.get('colorCode'))
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name),
                ('attribute_id', '=', color_attribute.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attribute.id
                })
            color_values.append(color_value.id)

        if color_values:
            attribute_lines.append((0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, color_values)]
            }))

        # Tallas
        size_values = []
        for size in product_data.get('sizes', []):
            size_name = size.get('size')
            size_value = self.env['product.attribute.value'].search([
                ('name', '=', size_name),
                ('attribute_id', '=', size_attribute.id)
            ], limit=1)
            if not size_value:
                size_value = self.env['product.attribute.value'].create({
                    'name': size_name,
                    'attribute_id': size_attribute.id
                })
            size_values.append(size_value.id)

        if size_values:
            attribute_lines.append((0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, size_values)]
            }))

        # Asignar líneas de atributos al template
        template.write({'attribute_line_ids': attribute_lines})

        _logger.info("✅ Producto creado correctamente con variantes de color y talla.")