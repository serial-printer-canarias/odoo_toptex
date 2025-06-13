import requests
import json
import base64
import io
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

        if not all([proxy_url, username, password, api_key]):
            _logger.error("Faltan parámetros de configuración.")
            return

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            _logger.error("Error autenticando con la API: %s", auth_response.text)
            return

        token = auth_response.json().get("token")
        if not token:
            _logger.error("No se recibió token válido")
            return

        _logger.info("Token recibido correctamente.")

        # Petición de producto (NS300 como prueba)
        catalog_reference = "ns300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error("Error consultando producto: %s", response.text)
            return

        data_list = response.json()
        _logger.info("Respuesta recibida: %s", json.dumps(data_list, indent=2))

        if isinstance(data_list, list) and data_list:
            data = data_list[0]
        else:
            _logger.error("No se encontró el producto en la respuesta.")
            return

        # Preparar datos básicos
        name = data.get('designation', {}).get('es', 'Producto sin nombre')
        brand_data = data.get('brand')
        brand = brand_data.get('name', {}).get('es') if brand_data else None
        description = data.get('description', {}).get('es', '')
        default_code = data.get('catalogReference', catalog_reference).upper()

        # Creamos o buscamos marca si viene
        brand_id = None
        if brand:
            brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_obj:
                brand_obj = self.env['product.brand'].create({'name': brand})
            brand_id = brand_obj.id

        # Crear plantilla
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'categ_id': self.env.ref('product.product_category_all').id,
            'product_brand_id': brand_id,
        }

        _logger.info("Datos para crear plantilla: %s", template_vals)
        product_template = self.create(template_vals)
        _logger.info("Plantilla creada: %s", product_template.name)

        # Preparar atributos de variantes
        attribute_lines = []

        # Colores
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        color_values = []
        for color in data.get('colors', []):
            color_name = color.get('name', {}).get('es', '')
            if color_name:
                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
                ], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({
                        'name': color_name,
                        'attribute_id': color_attr.id
                    })
                color_values.append(color_val.id)

        if color_values:
            attribute_lines.append((0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, color_values)]
            }))

        # Tallas
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        size_values = []
        sizes_collected = set()
        for color in data.get('colors', []):
            for size in color.get('sizes', []):
                size_name = size.get('size')
                if size_name and size_name not in sizes_collected:
                    sizes_collected.add(size_name)
                    size_val = self.env['product.attribute.value'].search([
                        ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                    ], limit=1)
                    if not size_val:
                        size_val = self.env['product.attribute.value'].create({
                            'name': size_name,
                            'attribute_id': size_attr.id
                        })
                    size_values.append(size_val.id)

        if size_values:
            attribute_lines.append((0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, size_values)]
            }))

        if attribute_lines:
            product_template.write({'attribute_line_ids': attribute_lines})
            _logger.info("Atributos y variantes creados correctamente.")

        # Imagen principal
        images = data.get('images', [])
        for img in images:
            img_url = img.get('url_packshot')
            if img_url:
                image_bin = self.get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info("Imagen principal asignada desde %s", img_url)
                break

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                img = Image.open(io.BytesIO(response.content))
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                return base64.b64encode(img_buffer.getvalue())
            else:
                _logger.warning("No se pudo descargar imagen o no es válida: %s", url)
                return None
        except Exception as e:
            _logger.error("Error descargando imagen: %s", str(e))
            return None