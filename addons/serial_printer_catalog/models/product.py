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
        # Leer parámetros de sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Obtener token
        token_url = f"{proxy_url}/v3/authenticate"
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        payload = {'username': username, 'password': password}

        response = requests.post(token_url, headers=headers, json=payload)
        if response.status_code != 200:
            _logger.error(f"Error autenticando: {response.status_code} - {response.text}")
            return

        token = response.json().get('token')
        _logger.info("Token obtenido correctamente")

        # Crear sesión persistente con headers fijos
        session = requests.Session()
        session.headers.update({
            'x-api-key': api_key,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        })

        # Endpoint individual b2b_uniquement estable
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products/{catalog_reference}?usage_right=b2b_uniquement"

        product_response = session.get(product_url)
        if product_response.status_code != 200:
            _logger.error(f"Error obteniendo producto: {product_response.status_code} - {product_response.text}")
            return

        product_data = product_response.json()
        _logger.info(f"Producto recibido: {json.dumps(product_data)}")

        # Obtener stock
        stock_url = f"{proxy_url}/v3/products/inventory/{catalog_reference}"
        stock_response = session.get(stock_url)
        if stock_response.status_code == 200:
            stock_data = stock_response.json()
            _logger.info(f"Stock recibido: {json.dumps(stock_data)}")
        else:
            stock_data = {}
            _logger.warning(f"No se pudo obtener el stock: {stock_response.status_code}")

        # Obtener precios de coste
        price_url = f"{proxy_url}/v3/products/price/{catalog_reference}"
        price_response = session.get(price_url)
        if price_response.status_code == 200:
            price_data = price_response.json()
            _logger.info(f"Precios recibidos: {json.dumps(price_data)}")
        else:
            price_data = {}
            _logger.warning(f"No se pudo obtener el precio: {price_response.status_code}")

        # Preparar atributos
        color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attribute:
            color_attribute = self.env['product.attribute'].create({'name': 'Color'})

        size_attribute = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attribute:
            size_attribute = self.env['product.attribute'].create({'name': 'Talla'})

        # Crear template principal
        brand_name = product_data.get('brand', {}).get('name', {}).get('es', 'Sin marca')
        description = product_data.get('description', {}).get('fullDescription', {}).get('es', '')
        template_vals = {
            'name': f"{brand_name} {product_data.get('designation', '')}",
            'default_code': product_data.get('catalogReference', ''),
            'type': 'consu',
            'detailed_type': 'product',
            'description_sale': description,
            'standard_price': price_data.get('priceList', [{}])[0].get('netPrice', 0.0),
            'list_price': price_data.get('priceList', [{}])[0].get('publicPrice', 0.0),
        }

        # Cargar imagen principal
        try:
            first_image_url = product_data.get('images', [])[0].get('url')
            image_response = requests.get(first_image_url)
            if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                image = Image.open(BytesIO(image_response.content))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue())
                template_vals['image_1920'] = img_str
            else:
                _logger.warning("No se pudo cargar la imagen principal")
        except Exception as e:
            _logger.warning(f"Error cargando imagen principal: {str(e)}")

        product_template = self.env['product.template'].create(template_vals)

        # Crear variantes
        for color in product_data.get('colors', []):
            color_name = color.get('translatedName', {}).get('es', color.get('name', ''))
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attribute.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name, 'attribute_id': color_attribute.id
                })

            for size in color.get('sizes', []):
                size_name = size.get('translatedName', {}).get('es', size.get('name', ''))
                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attribute.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': size_attribute.id
                    })

                combination = [(6, 0, [color_value.id, size_value.id])]

                variant = self.env['product.product'].create({
                    'product_tmpl_id': product_template.id,
                    'attribute_value_ids': combination,
                    'default_code': size.get('sku', ''),
                    'standard_price': price_data.get('priceList', [{}])[0].get('netPrice', 0.0),
                })

                # Descargar imagen por variante (color)
                try:
                    variant_images = color.get('images', [])
                    if variant_images:
                        variant_image_url = variant_images[0].get('url')
                        image_response = requests.get(variant_image_url)
                        if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                            image = Image.open(BytesIO(image_response.content))
                            buffered = BytesIO()
                            image.save(buffered, format="PNG")
                            img_str = base64.b64encode(buffered.getvalue())
                            variant.image_1920 = img_str
                        else:
                            _logger.warning(f"No se pudo cargar imagen variante para color {color_name}")
                except Exception as e:
                    _logger.warning(f"Error cargando imagen variante: {str(e)}")

                # Asignar stock real si disponible
                try:
                    inventory = stock_data.get('inventoryList', [])
                    for inv in inventory:
                        if inv.get('sku') == size.get('sku'):
                            qty = inv.get('availableQuantity', 0)
                            self.env['stock.quant'].create({
                                'product_id': variant.id,
                                'location_id': 1,  # Ajustar si es necesario
                                'quantity': qty
                            })
                            break
                except Exception as e:
                    _logger.warning(f"Error asignando stock: {str(e)}")

        _logger.info("Producto sincronizado correctamente")