import base64
import json
import logging
from io import BytesIO
from PIL import Image
import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            _logger.error("Faltan parámetros de configuración.")
            return

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json',
        }
        auth_data = {
            'username': username,
            'password': password,
        }
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_data)
        if auth_response.status_code != 200:
            _logger.error(f"Error autenticando: {auth_response.status_code} {auth_response.text}")
            return
        token = auth_response.json().get('token')

        # Configurar headers autenticados
        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token,
            'Accept': 'application/json',
        }

        # Obtener datos del producto NS300
        catalog_ref = 'NS300'
        product_url = f"{proxy_url}/v3/products/{catalog_ref}?usage_right=b2b_uniquement"
        product_response = requests.get(product_url, headers=headers)
        if product_response.status_code != 200:
            _logger.error(f"Error producto: {product_response.status_code} {product_response.text}")
            return
        product_data = product_response.json()
        _logger.info("PRODUCTO JSON -> %s", json.dumps(product_data, indent=2))

        # Obtener stock
        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        inventory_response = requests.get(inventory_url, headers=headers)
        stock_quantity = 0
        if inventory_response.status_code == 200:
            inventory_data = inventory_response.json()
            for item in inventory_data.get("inventory", []):
                stock_quantity += int(item.get("stock", 0))
        else:
            _logger.warning("No se pudo obtener stock.")

        # Obtener precio de coste
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
        price_response = requests.get(price_url, headers=headers)
        standard_price = 0.0
        if price_response.status_code == 200:
            price_data = price_response.json()
            prices = price_data.get("prices", [])
            if prices:
                standard_price = float(prices[0].get("price", 0.0))
        else:
            _logger.warning("No se pudo obtener precio de coste.")

        # Extraer info principal
        name = f"{product_data.get('brand', {}).get('name', {}).get('es', '')} {product_data.get('translatedName', {}).get('es', '')}"
        description = product_data.get('description', {}).get('es', '')
        brand_name = product_data.get('brand', {}).get('name', {}).get('es', 'Sin marca')

        # Categoría por defecto (crear si no existe)
        categ = self.env['product.category'].search([('name', '=', 'TopTex')], limit=1)
        if not categ:
            categ = self.env['product.category'].create({'name': 'TopTex'})

        # Crear marca como categoría si se desea usar marca como categoría
        brand_categ = self.env['product.category'].search([('name', '=', brand_name)], limit=1)
        if not brand_categ:
            brand_categ = self.env['product.category'].create({'name': brand_name})

        # Imagen principal
        image_url = product_data.get("images", {}).get("packshotUrl")
        image_1920 = False
        if image_url:
            try:
                img_resp = requests.get(f"{proxy_url}/{image_url}")
                if img_resp.status_code == 200 and 'image' in img_resp.headers.get('Content-Type', ''):
                    image = Image.open(BytesIO(img_resp.content))
                    buffer = BytesIO()
                    image.save(buffer, format='PNG')
                    image_1920 = base64.b64encode(buffer.getvalue())
            except Exception as e:
                _logger.warning(f"Error cargando imagen principal: {e}")

        # Atributos y variantes
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        variant_lines = []

        for color in product_data.get("colors", []):
            color_name = color.get("name", {}).get("es")
            if not color_name:
                continue

            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name),
                ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })
            color_values.append(color_val.id)

        size_values = []
        for size in product_data.get("sizes", []):
            size_name = size.get("name")
            if not size_name:
                continue

            size_val = self.env['product.attribute.value'].search([
                ('name', '=', size_name),
                ('attribute_id', '=', size_attr.id)
            ], limit=1)
            if not size_val:
                size_val = self.env['product.attribute.value'].create({
                    'name': size_name,
                    'attribute_id': size_attr.id
                })
            size_values.append(size_val.id)

        # Crear product.template
        template = self.env['product.template'].create({
            'name': name,
            'default_code': catalog_ref,
            'type': 'consu',
            'categ_id': brand_categ.id,
            'image_1920': image_1920,
            'description_sale': description,
            'standard_price': standard_price,
            'list_price': standard_price * 2.0,
            'detailed_type': 'consu',
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, color_values)]
                }),
                (0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, size_values)]
                })
            ],
        })

        _logger.info("Producto NS300 creado correctamente con todas las variantes.")