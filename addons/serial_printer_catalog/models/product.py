# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models, api, exceptions

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise exceptions.UserError("❌ Faltan credenciales o parámetros.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {'username': username, 'password': password}
        auth_headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            raise exceptions.UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise exceptions.UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        catalog_reference = "NS300"

        # Obtener producto
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise exceptions.UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
        data_list = response.json()
        data = data_list[0] if isinstance(data_list, list) else data_list

        _logger.info("✅ Producto recibido correctamente.")

        # Obtener stock
        stock_url = f"{proxy_url}/v3/products/inventory/{catalog_reference}"
        stock_response = requests.get(stock_url, headers=headers)
        stock_data = stock_response.json() if stock_response.status_code == 200 else {}

        # Obtener precios
        price_url = f"{proxy_url}/v3/products/price/{catalog_reference}"
        price_response = requests.get(price_url, headers=headers)
        price_data = price_response.json() if price_response.status_code == 200 else {}

        # Marca
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        list_price = price_data.get('priceList', [{}])[0].get('publicPrice', 9.8)
        standard_price = price_data.get('priceList', [{}])[0].get('netPrice', 0.0)

        # Imagen principal
        image_data = None
        try:
            first_image_url = data.get("images", [])[0].get("url")
            image_response = requests.get(first_image_url)
            if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                image = Image.open(BytesIO(image_response.content))
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                image_data = base64.b64encode(buffered.getvalue())
        except Exception as e:
            _logger.warning(f"⚠️ Error imagen principal: {e}")

        # Crear atributos (si no existen)
        color_attribute = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attribute:
            color_attribute = self.env['product.attribute'].create({'name': 'Color'})

        size_attribute = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attribute:
            size_attribute = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in data.get("colors", []):
            color_name = color.get("translatedName", {}).get("es", color.get("name", ""))
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attribute.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attribute.id})
            color_values.append(color_value)

            for size in color.get("sizes", []):
                size_name = size.get("translatedName", {}).get("es", size.get("name", ""))
                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attribute.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attribute.id})
                size_values.append(size_value)

        # Crear el producto template sin variantes primero
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref('product.product_category_all').id,
        }
        if image_data:
            template_vals['image_1920'] = image_data

        product_template = self.env['product.template'].create(template_vals)

        # Asignar atributos después vía write
        product_template.write({
            'attribute_line_ids': [
                (0, 0, {'attribute_id': color_attribute.id, 'value_ids': [(6, 0, [v.id for v in color_values])]}),
                (0, 0, {'attribute_id': size_attribute.id, 'value_ids': [(6, 0, [v.id for v in size_values])]}),
            ]
        })

        # Forzar generación de variantes
        product_template._create_variant_ids()

        # Recorrer variantes
        for variant in product_template.product_variant_ids:
            variant_attributes = variant.product_template_attribute_value_ids
            color_name = ''
            for val in variant_attributes:
                if val.attribute_id == color_attribute:
                    color_name = val.name

            # Imagen de variante por color
            try:
                for color in data.get("colors", []):
                    color_es = color.get("translatedName", {}).get("es", color.get("name", ""))
                    if color_es == color_name:
                        variant_images = color.get("images", [])
                        if variant_images:
                            variant_image_url = variant_images[0].get("url")
                            image_response = requests.get(variant_image_url)
                            if image_response.status_code == 200 and 'image' in image_response.headers.get('Content-Type', ''):
                                image = Image.open(BytesIO(image_response.content))
                                buffered = BytesIO()
                                image.save(buffered, format="PNG")
                                img_str = base64.b64encode(buffered.getvalue())
                                variant.image_1920 = img_str
                        break
            except Exception as e:
                _logger.warning(f"⚠️ Error imagen variante: {e}")

            # Stock por SKU
            try:
                inventory = stock_data.get("inventoryList", [])
                for inv in inventory:
                    if inv.get("sku") == variant.default_code:
                        qty = inv.get("availableQuantity", 0)
                        self.env['stock.quant'].create({
                            'product_id': variant.id,
                            'location_id': 1,
                            'quantity': qty
                        })
                        break
            except Exception as e:
                _logger.warning(f"⚠️ Error stock variante: {e}")

        _logger.info("✅ Producto NS300 completamente sincronizado.")