import json
import base64
import requests
from io import BytesIO
from PIL import Image
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros desde Odoo
        IrConfig = self.env['ir.config_parameter'].sudo()
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')
        proxy_url = IrConfig.get_param('toptex_proxy_url')

        # Generar token desde proxy
        auth_url = f'{proxy_url}/v3/authenticate'
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}

        try:
            auth_response = requests.post(auth_url, headers=headers, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json().get('token')
            if not token:
                _logger.error('❌ No se pudo obtener el token de autenticación')
                return
            _logger.info('✅ Token recibido correctamente.')
        except Exception as e:
            _logger.error(f'❌ Error autenticando: {e}')
            return

        # Descargar datos del producto (por catalog_reference)
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        product_headers = {
            'x-api-key': api_key,
            'toptex-authorization': token,
            'Content-Type': 'application/json'
        }

        try:
            product_response = requests.get(product_url, headers=product_headers)
            if product_response.status_code != 200:
                _logger.error(f"❌ Error en llamada de producto: {product_response.status_code}")
                return
            product_data = product_response.json()
            _logger.info(f"✅ JSON principal recibido: {json.dumps(product_data)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener datos del producto: {e}")
            return

        # Procesar respuesta (puede venir dict o list)
        if isinstance(product_data, dict):
            products = [product_data]
        elif isinstance(product_data, list):
            products = product_data
        else:
            _logger.error("❌ Formato de datos no reconocido")
            return

        for product in products:
            name = product.get("translatedName", {}).get("es", "SIN NOMBRE")
            default_code = product.get("catalogReference", "SIN_REF")
            description = product.get("description", {}).get("es", "")
            brand_data = product.get("brand")
            brand_name = brand_data.get("name", {}).get("es") if brand_data else "Sin Marca"
            color_variants = product.get("colors", [])
            categ_id = self.env['product.category'].search([('name', '=', 'All')], limit=1).id

            # Crear o buscar marca
            brand_obj = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
            if not brand_obj:
                brand_obj = self.env['product.brand'].create({'name': brand_name})

            # Crear atributos
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})

            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

            # Preparar valores de variantes
            color_values = []
            size_values = []
            for color in color_variants:
                color_name = color.get("translatedColorName", {}).get("es", "")
                if color_name:
                    val = self.env['product.attribute.value'].search([
                        ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
                    ], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({
                            'name': color_name,
                            'attribute_id': color_attr.id
                        })
                    color_values.append(val.id)

                for size in color.get("sizes", []):
                    size_name = size.get("size", "")
                    if size_name:
                        val = self.env['product.attribute.value'].search([
                            ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                        ], limit=1)
                        if not val:
                            val = self.env['product.attribute.value'].create({
                                'name': size_name,
                                'attribute_id': size_attr.id
                            })
                        size_values.append(val.id)

            # Eliminar duplicados
            size_values = list(set(size_values))

            # Crear el producto template
            product_template = self.env['product.template'].create({
                'name': name,
                'default_code': default_code,
                'description_sale': description,
                'categ_id': categ_id,
                'standard_price': 0.0,
                'list_price': 0.0,
                'type': 'product',
                'product_brand_id': brand_obj.id,
                'attribute_line_ids': [
                    (0, 0, {
                        'attribute_id': color_attr.id,
                        'value_ids': [(6, 0, color_values)]
                    }),
                    (0, 0, {
                        'attribute_id': size_attr.id,
                        'value_ids': [(6, 0, size_values)]
                    }),
                ]
            })

            # Descargar imagen principal
            image_url = product.get("images", [{}])[0].get("url", "")
            if image_url:
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        img = Image.open(BytesIO(image_response.content))
                        img = img.convert('RGB')
                        img_byte_arr = BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        product_template.image_1920 = base64.b64encode(img_byte_arr.getvalue())
                        _logger.info("✅ Imagen principal descargada correctamente")
                except Exception as e:
                    _logger.warning(f"⚠ No se pudo cargar la imagen: {e}")

            _logger.info(f"✅ Producto {default_code} sincronizado completamente.")