import requests
import json
import base64
from io import BytesIO
from PIL import Image
from odoo import models, fields, api
import logging

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
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        token = auth_response.json().get("token")
        _logger.info("Token recibido correctamente.")

        # Descargar producto por catalog_reference NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=NS300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            _logger.error(f"Error en llamada a catálogo: {response.text}")
            return

        data_list = response.json()
        if isinstance(data_list, list) and len(data_list) > 0:
            data = data_list[0]
        else:
            _logger.error("No se encontró producto en respuesta.")
            return

        _logger.info("JSON principal recibido:")
        _logger.info(json.dumps(data, indent=2))

        # Extraer campos generales
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        brand_data = data.get("brand", {})
        brand = brand_data.get("name", {}).get("es", "Sin Marca")

        brand_category = self.env['product.category'].search([('name', '=', brand)], limit=1)
        if not brand_category:
            brand_category = self.env['product.category'].create({'name': brand})

        # Imagen principal
        image_bin = False
        images = data.get("images", [])
        if images:
            image_url = images[0].get("url_packshot")
            if image_url:
                try:
                    img_response = requests.get(image_url)
                    img = Image.open(BytesIO(img_response.content))
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    image_bin = base64.b64encode(buffer.getvalue())
                except Exception as e:
                    _logger.warning(f"No se pudo procesar imagen principal: {str(e)}")

        # Obtener precio coste
        price_url = f"{proxy_url}/v3/products/price?catalog_reference=NS300"
        price_response = requests.get(price_url, headers=headers)
        standard_price = 0.0
        if price_response.status_code == 200:
            price_data = price_response.json()
            price_list = price_data.get("prices", [])
            if price_list:
                standard_price = price_list[0].get("netPrice", 0.0)
            else:
                _logger.warning("Lista de precios vacía.")
        else:
            _logger.warning("Error obteniendo precios.")

        # Obtener stock
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference=NS300"
        stock_response = requests.get(stock_url, headers=headers)
        stock_quantity = 0
        if stock_response.status_code == 200:
            stock_data = stock_response.json()
            stock_quantity = sum(item.get("availableStock", 0) for item in stock_data.get("inventory", []))
        else:
            _logger.warning("Error obteniendo stock.")

        # Crear plantilla principal
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'categ_id': brand_category.id,
            'image_1920': image_bin or False,
            'standard_price': standard_price,
            'list_price': standard_price * 2,
        }

        product_template = self.create(template_vals)
        _logger.info(f"Producto creado: {product_template.name}")

        # Crear atributos Color y Talla
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        attribute_lines = []
        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es", "").strip()
            if not color_name:
                _logger.warning("Color vacío, omitido.")
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

            for size in color.get("sizes", []):
                size_name = size.get("size", "").strip()
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

                attribute_lines.append((0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [color_val.id])]
                }))
                attribute_lines.append((0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [size_val.id])]
                }))

        if attribute_lines:
            product_template.write({'attribute_line_ids': attribute_lines})
            _logger.info("Atributos y variantes asignadas correctamente.")

        # Log final para validación completa
        _logger.info("Producto NS300 sincronizado completamente en Odoo.")