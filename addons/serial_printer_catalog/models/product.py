import base64
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
        config = self.env['ir.config_parameter'].sudo()
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        api_key = config.get_param('toptex_api_key')
        proxy_url = config.get_param('toptex_proxy_url')

        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        auth_response = requests.post(f"{proxy_url}/v3/authenticate", headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            _logger.error(f"Error autenticando: {auth_response.text}")
            return

        token = auth_response.json().get("token")
        if not token:
            _logger.error("Token vacío.")
            return

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json"
        }

        catalog_ref = "NS300"

        # Producto
        url_product = f"{proxy_url}/v3/products/{catalog_ref}?usage_right=b2b_uniquement"
        response = requests.get(url_product, headers=headers)
        if response.status_code != 200:
            _logger.error(f"Error producto: {response.text}")
            return

        product_data = response.json()

        # Precio coste
        url_price = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
        price_response = requests.get(url_price, headers=headers)
        standard_price = 0.0
        if price_response.status_code == 200:
            try:
                standard_price = float(price_response.json()[0].get("price", 0.0))
            except Exception as e:
                _logger.warning(f"Precio no válido: {str(e)}")

        # Stock total
        url_stock = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        stock_response = requests.get(url_stock, headers=headers)
        inventory = 0
        if stock_response.status_code == 200:
            try:
                inventory = sum(int(s.get("stock", 0)) for s in stock_response.json())
            except Exception as e:
                _logger.warning(f"Stock no válido: {str(e)}")

        # Campos básicos
        name = product_data.get("translatedName", {}).get("es") or product_data.get("designation")
        description = product_data.get("description", {}).get("es", "")
        brand_data = product_data.get("brand", {})
        brand_name = brand_data.get("name", {}).get("es") if isinstance(brand_data, dict) else "Sin marca"
        colors = product_data.get("colors", [])
        sizes = product_data.get("sizes", [])

        # Categoría = marca
        brand_category = self.env['product.category'].search([('name', '=', brand_name)], limit=1)
        if not brand_category:
            brand_category = self.env['product.category'].create({'name': brand_name})

        # Atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # Crear product.template
        template = self.create({
            'name': f"{brand_name} {name}",
            'type': 'product',
            'categ_id': brand_category.id,
            'description_sale': description,
            'standard_price': standard_price,
            'list_price': standard_price * 2,
            'image_1920': False,
        })

        # Variantes
        for color in colors:
            color_name = color.get("translatedValue", {}).get("es") or color.get("value")
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })

            for size in sizes:
                size_name = size.get("translatedValue", {}).get("es") or size.get("value")
                size_value = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_value:
                    size_value = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attr.id
                    })

                variant = self.env['product.product'].create({
                    'product_tmpl_id': template.id,
                    'attribute_value_ids': [(6, 0, [color_value.id, size_value.id])],
                    'standard_price': standard_price,
                })

                # Imagen por color
                try:
                    images = color.get("images", [])
                    if images:
                        img_url = images[0].get("url")
                        img_resp = requests.get(img_url)
                        if img_resp.status_code == 200 and "image" in img_resp.headers.get("Content-Type", ""):
                            image = Image.open(BytesIO(img_resp.content))
                            buffer = BytesIO()
                            image.save(buffer, format='PNG')
                            variant.image_1920 = base64.b64encode(buffer.getvalue())
                except Exception as e:
                    _logger.warning(f"Error imagen variante {color_name}: {str(e)}")

        _logger.info(f"Producto {catalog_ref} creado con marca {brand_name}, stock {inventory} y variantes.")