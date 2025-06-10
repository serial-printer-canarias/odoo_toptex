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
        # PARÁMETROS
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        catalog_reference = 'NS300'

        # TOKEN
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(f"{proxy_url}/v3/authenticate", json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")

        if not token:
            _logger.error("Autenticación fallida. No se recibió token.")
            return

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Content-Type": "application/json"
        }

        # LLAMADAS API
        product_url = f"{proxy_url}/v3/products/reference/{catalog_reference}?usage_right=b2b_uniquement"
        price_url = f"{proxy_url}/v3/products/price/{catalog_reference}"
        stock_url = f"{proxy_url}/v3/products/inventory/{catalog_reference}"

        product_data = requests.get(product_url, headers=headers).json()
        price_data = requests.get(price_url, headers=headers).json()
        stock_data = requests.get(stock_url, headers=headers).json()

        _logger.info(f"PRODUCTO JSON: {product_data}")
        _logger.info(f"PRECIO JSON: {price_data}")
        _logger.info(f"STOCK JSON: {stock_data}")

        translated_name = product_data.get('translatedName', {}).get('es', 'Sin nombre')
        description = product_data.get('translatedDescription', {}).get('es', '')
        brand = product_data.get('brand', {}).get('name', {}).get('es', 'Sin marca')
        base_image_url = product_data.get('images', [])[0] if product_data.get('images') else None
        colors = product_data.get('colors', [])
        sizes = product_data.get('sizes', [])

        # CATEGORÍA (requerida)
        categ_id = self.env['product.category'].search([('name', '=', 'All')], limit=1).id

        # CREAR O ACTUALIZAR TEMPLATE
        template = self.env['product.template'].create({
            'name': f"{translated_name} - {brand}",
            'default_code': catalog_reference,
            'description_sale': description,
            'type': 'product',
            'categ_id': categ_id,
            'standard_price': price_data.get('unitCostPrice', 0.0),
            'image_1920': self._get_image_binary(base_image_url, proxy_url) if base_image_url else False,
        })

        # CREAR ATRIBUTOS: COLOR Y TALLA
        attr_color = self._get_or_create_attribute('Color')
        attr_size = self._get_or_create_attribute('Talla')

        for color in colors:
            color_name = color.get('translatedName', {}).get('es', 'Sin nombre')
            color_code = color.get('colorCode')
            color_image_url = color.get('packshotUrl')

            color_value = self._get_or_create_attribute_value(attr_color, color_name)

            for size in sizes:
                size_name = size.get('translatedName', {}).get('es', 'Sin talla')
                size_value = self._get_or_create_attribute_value(attr_size, size_name)

                variant = self.env['product.product'].create({
                    'product_tmpl_id': template.id,
                    'attribute_value_ids': [(6, 0, [color_value.id, size_value.id])],
                    'default_code': f"{catalog_reference}_{color.get('id')}_{size.get('id')}",
                    'image_1920': self._get_image_binary(color_image_url, proxy_url) if color_image_url else False,
                    'standard_price': price_data.get('unitCostPrice', 0.0),
                    'qty_available': self._get_stock_qty(stock_data, color_code, size.get('id')),
                })

    def _get_or_create_attribute(self, name):
        return self.env['product.attribute'].search([('name', '=', name)], limit=1) or \
               self.env['product.attribute'].create({'name': name})

    def _get_or_create_attribute_value(self, attribute, name):
        return self.env['product.attribute.value'].search([('name', '=', name), ('attribute_id', '=', attribute.id)], limit=1) or \
               self.env['product.attribute.value'].create({'name': name, 'attribute_id': attribute.id})

    def _get_image_binary(self, image_url, proxy_url):
        try:
            full_url = f"{proxy_url}/{image_url}"
            response = requests.get(full_url, stream=True)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                img = Image.open(BytesIO(response.content))
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                return base64.b64encode(buffer.getvalue())
        except Exception as e:
            _logger.warning(f"Error procesando imagen {image_url}: {e}")
        return False

    def _get_stock_qty(self, stock_data, color_code, size_id):
        try:
            for item in stock_data.get('stock', []):
                if item.get('colorCode') == color_code and item.get('sizeId') == size_id:
                    return item.get('quantity', 0.0)
        except Exception as e:
            _logger.warning(f"Error procesando stock para {color_code}-{size_id}: {e}")
        return 0.0