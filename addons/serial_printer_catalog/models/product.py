# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Obtener parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        catalog_reference = 'NS300'  # Producto base a importar

        # URL de autenticación
        auth_url = f'{proxy_url}/v3/authenticate'

        # Headers de autenticación
        auth_headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip',
        }

        # Payload de autenticación
        auth_payload = {
            'username': username,
            'password': password
        }

        # Obtener token
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        _logger.info(f'Auth status: {auth_response.status_code}')
        if auth_response.status_code != 200:
            _logger.error('Error en autenticación')
            return

        token = auth_response.json().get('token')
        if not token:
            _logger.error('Token no recibido')
            return

        # Headers para peticiones con token
        headers = {
            'x-api-key': api_key,
            'toptex-authorization': token,
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip',
        }

        # URL de producto
        product_url = f'{proxy_url}/v3/products/{catalog_reference}?usage_right=b2b_b2c'
        response = requests.get(product_url, headers=headers)
        _logger.info(f'Product status: {response.status_code}')
        if response.status_code != 200:
            _logger.error('Error al obtener producto')
            return

        data = response.json()
        _logger.info(f'JSON recibido: {json.dumps(data, indent=2)}')

        # Obtener o crear marca
        brand = data.get('brand', {}).get('name', '')
        brand_id = False
        if brand:
            brand_id = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_id:
                brand_id = self.env['product.brand'].create({'name': brand})

        # Crear atributos si no existen
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        attribute_line_ids = []
        product_variants = []

        for color in data.get('colors', []):
            color_name = color.get('translatedName', {}).get('es', '')
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

            for size in color.get('sizes', []):
                size_name = size.get('translatedName', {}).get('es', '')
                if not size_name:
                    continue

                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attr.id
                    })

                # Crear variante
                variant = {
                    'attribute_value_ids': [(6, 0, [color_value.id, size_value.id])],
                    'default_code': size.get('sku'),
                }

                # Imagen por color
                image_url = color.get('media', {}).get('images', [{}])[0].get('url', '')
                if image_url:
                    try:
                        image_response = requests.get(image_url)
                        image = Image.open(BytesIO(image_response.content))
                        img_byte_arr = BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        variant['image_1920'] = base64.b64encode(img_byte_arr.getvalue())
                    except Exception as e:
                        _logger.warning(f'Error al procesar imagen de variante: {e}')

                product_variants.append(variant)

        # Línea de atributos para el template
        attribute_line_ids = [
            (0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, color_attr.value_ids.ids)]
            }),
            (0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, size_attr.value_ids.ids)]
            })
        ]

        # Imagen principal
        main_image = data.get('media', {}).get('images', [{}])[0].get('url', '')
        image_1920 = False
        if main_image:
            try:
                image_response = requests.get(main_image)
                image = Image.open(BytesIO(image_response.content))
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                image_1920 = base64.b64encode(img_byte_arr.getvalue())
            except Exception as e:
                _logger.warning(f'Error al procesar imagen principal: {e}')

        # Obtener precio de coste
        price_url = f'{proxy_url}/v3/products/price?catalog_reference={catalog_reference}'
        price_response = requests.get(price_url, headers=headers)
        standard_price = 0.0
        if price_response.status_code == 200:
            price_data = price_response.json()
            try:
                standard_price = float(price_data[0].get('price', 0.0))
            except Exception as e:
                _logger.warning(f'Error al obtener precio de coste: {e}')

        # Obtener stock
        stock_url = f'{proxy_url}/v3/products/inventory?catalog_reference={catalog_reference}'
        stock_response = requests.get(stock_url, headers=headers)
        qty_available = 0
        if stock_response.status_code == 200:
            stock_data = stock_response.json()
            try:
                for item in stock_data:
                    qty_available += int(item.get('stock', 0))
            except Exception as e:
                _logger.warning(f'Error al obtener stock: {e}')

        # Crear el template
        self.create({
            'name': data.get('translatedName', {}).get('es', 'Sin nombre'),
            'default_code': catalog_reference,
            'type': 'consu',
            'list_price': 0.0,
            'standard_price': standard_price,
            'description_sale': data.get('translatedDescription', {}).get('es', ''),
            'image_1920': image_1920,
            'attribute_line_ids': attribute_line_ids,
            'product_variant_ids': [(0, 0, v) for v in product_variants],
            'qty_available': qty_available,
            'brand_id': brand_id.id if brand_id else False,
        })