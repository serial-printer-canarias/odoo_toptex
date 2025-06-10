import json
import base64
import requests
import logging
from io import BytesIO
from PIL import Image
from odoo import models, api

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        api_key = ir_config.get_param('toptex_api_key')
        proxy_url = ir_config.get_param('toptex_proxy_url')
        catalog_ref = "NS300"

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, headers=headers, json=payload)
        token = auth_response.json().get("token")

        if not token:
            _logger.error("Error al autenticar con TopTex")
            return

        common_headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        # Obtener info del producto por catalog_ref
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_uniquement"
        r_product = requests.get(product_url, headers=common_headers)
        product_data = r_product.json()

        if not product_data:
            _logger.warning("Respuesta vacía de producto")
            return

        product = product_data[0] if isinstance(product_data, list) else product_data
        _logger.info(f"JSON Producto: {json.dumps(product, indent=2)}")

        name = f"{product.get('brand', {}).get('name', {}).get('es', '')} {product.get('translatedName', {}).get('es', '')}".strip()
        description = product.get('description', {}).get('es', '')
        brand = product.get('brand', {}).get('name', {}).get('es', '')
        default_code = catalog_ref
        list_price = product.get("publicPrice", 0)
        standard_price = 0.0

        # Obtener precio de coste real
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}&usage_right=b2b_uniquement"
        r_price = requests.get(price_url, headers=common_headers)
        price_json = r_price.json()
        standard_price = price_json.get("variants", [{}])[0].get("price", 0.0)

        # Obtener stock real
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        r_stock = requests.get(stock_url, headers=common_headers)
        stock_json = r_stock.json()
        stock_data = {item.get("sku"): item.get("stock", 0) for item in stock_json.get("inventory", [])}

        # Crear categoría dummy si no existe
        categ = self.env['product.category'].search([('name', '=', 'TopTex')], limit=1)
        if not categ:
            categ = self.env['product.category'].create({'name': 'TopTex'})

        # Descargar imagen principal
        image_url = product.get("images", {}).get("product", {}).get("url")
        image_1920 = None
        if image_url:
            try:
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    image_1920 = base64.b64encode(buffer.getvalue())
                else:
                    _logger.warning("No se pudo descargar imagen principal")
            except Exception as e:
                _logger.warning(f"Error descargando imagen principal: {e}")

        # Crear atributos Color y Talla
        attr_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not attr_color:
            attr_color = self.env['product.attribute'].create({'name': 'Color'})

        attr_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not attr_size:
            attr_size = self.env['product.attribute'].create({'name': 'Talla'})

        # Crear producto.template
        template = self.create({
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'list_price': list_price,
            'standard_price': standard_price,
            'description_sale': description,
            'image_1920': image_1920,
            'categ_id': categ.id,
            'attribute_line_ids': [(5, 0, 0)],
        })

        variant_combinations = []
        colors = product.get("colors", [])
        sizes = product.get("sizes", [])

        for color in colors:
            color_name = color.get("translatedName", {}).get("es", "")
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', attr_color.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name, 'attribute_id': attr_color.id
                })

            for size in sizes:
                size_name = size.get("translatedName", {}).get("es", "")
                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', attr_size.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': attr_size.id
                    })

                # Buscar SKU de la variante
                sku = size.get("sku", {}).get(color.get("id", ""), "")
                stock_qty = stock_data.get(sku, 0)

                # Imagen por color
                img_url = color.get("images", {}).get("product", {}).get("url")
                image_variant = None
                if img_url:
                    try:
                        img_response = requests.get(img_url)
                        if img_response.status_code == 200:
                            image = Image.open(BytesIO(img_response.content))
                            buffer = BytesIO()
                            image.save(buffer, format="PNG")
                            image_variant = base64.b64encode(buffer.getvalue())
                    except Exception as e:
                        _logger.warning(f"Error imagen variante: {e}")

                variant_combinations.append((0, 0, {
                    'product_tmpl_id': template.id,
                    'default_code': sku,
                    'attribute_value_ids': [(6, 0, [color_value.id, size_value.id])],
                    'image_1920': image_variant,
                    'qty_available': stock_qty
                }))

        # Añadir líneas de atributos al template
        template.write({
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': attr_color.id,
                    'value_ids': [(6, 0, attr_color.value_ids.ids)]
                }),
                (0, 0, {
                    'attribute_id': attr_size.id,
                    'value_ids': [(6, 0, attr_size.value_ids.ids)]
                })
            ]
        })

        # Crear variantes
        self.env['product.product'].create(variant_combinations)
        _logger.info("Producto NS300 creado correctamente con variantes.")