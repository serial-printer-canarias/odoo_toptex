# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Autenticación (POST con API Key)
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        auth_payload = {
            'username': username,
            'password': password
        }

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            _logger.error(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            return

        token = auth_response.json().get('token')
        if not token:
            _logger.error("❌ No se recibió un token válido.")
            return

        _logger.info("🔐 Token recibido correctamente.")

        # Headers para TODAS las llamadas GET
        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token,
            'Content-Type': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br'
        }

        catalog_reference = "NS300"

        # Llamada al producto
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"❌ Error obteniendo producto: {response.status_code} - {response.text}")
            return

        data_list = response.json()
        if isinstance(data_list, list) and len(data_list) > 0:
            product_data = data_list[0]
        else:
            _logger.error("❌ No se encontró el producto en la respuesta.")
            return

        _logger.info("✅ Producto recibido correctamente.")

        # Llamada a stock
        stock_url = f"{proxy_url}/v3/products/inventory/{catalog_reference}"
        stock_response = requests.get(stock_url, headers=headers)
        stock_data = stock_response.json() if stock_response.status_code == 200 else {}

        # Llamada a precios
        price_url = f"{proxy_url}/v3/products/price/{catalog_reference}"
        price_response = requests.get(price_url, headers=headers)
        price_data = price_response.json() if price_response.status_code == 200 else {}

        # Preparación de atributos
        color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attribute:
            color_attribute = self.env['product.attribute'].create({'name': 'Color'})

        size_attribute = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attribute:
            size_attribute = self.env['product.attribute'].create({'name': 'Talla'})

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

        try:
            first_image_url = product_data.get('images', [])[0].get('url')
            image_response = requests.get(first_image_url)
            if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                image = Image.open(BytesIO(image_response.content))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue())
                template_vals['image_1920'] = img_str
        except Exception as e:
            _logger.warning(f"⚠️ Error cargando imagen principal: {str(e)}")

        product_template = self.env['product.template'].create(template_vals)

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
                except Exception as e:
                    _logger.warning(f"⚠️ Error cargando imagen variante: {str(e)}")

                try:
                    inventory = stock_data.get('inventoryList', [])
                    for inv in inventory:
                        if inv.get('sku') == size.get('sku'):
                            qty = inv.get('availableQuantity', 0)
                            self.env['stock.quant'].create({
                                'product_id': variant.id,
                                'location_id': 1,
                                'quantity': qty
                            })
                            break
                except Exception as e:
                    _logger.warning(f"⚠️ Error asignando stock: {str(e)}")

        _logger.info("✅ Producto sincronizado correctamente.")