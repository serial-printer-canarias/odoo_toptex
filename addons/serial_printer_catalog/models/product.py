import requests
import base64
import logging
import json
from odoo import models
from PIL import Image
from io import BytesIO

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format='PNG')
                return base64.b64encode(img_byte_arr.getvalue())
            else:
                _logger.warning(f"Error al descargar imagen: {url}")
        except Exception as e:
            _logger.error(f"Error procesando imagen: {e}")
        return False

    def sync_product_from_api(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers_auth = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_data = {"username": username, "password": password}
        response = requests.post(auth_url, headers=headers_auth, json=auth_data)

        if response.status_code != 200:
            _logger.error(f"Error autenticando: {response.text}")
            return

        token = response.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        product_url = f"{proxy_url}/v3/products?catalog_reference=NS300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        _logger.info(f"📦 Respuesta cruda:\n{response.text}")

        if response.status_code != 200:
            _logger.error(f"Error al obtener producto: {response.text}")
            return

        try:
            data_list = response.json()
            if isinstance(data_list, list) and len(data_list) > 0:
                data = data_list[0]
            else:
                _logger.error("❌ No se encontró el producto en la respuesta")
                return
        except Exception as e:
            _logger.error(f"Error interpretando JSON: {e}")
            return

        _logger.info("✅ JSON interpretado correctamente.")

        # Extraemos campos básicos
        name = data.get('designation', {}).get('es', 'Producto sin nombre')
        description = data.get('description', {}).get('es', '')
        default_code = data.get('catalogReference', 'NS300')
        brand_data = data.get('brand', {})
        brand = brand_data.get('name', {}).get('es', '') if brand_data else ''

        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': 0.0,
            'standard_price': 0.0,
            'categ_id': self.env.ref('product.product_category_all').id
        }

        if brand:
            template_vals['part_number'] = brand  # (opcional: luego podemos crear campo marca real)

        _logger.info(f"📝 Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Atributos y variantes
        attribute_lines = []

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color_data in data.get('colors', []):
            color_name = color_data.get('colors', {}).get('es')
            if not color_name:
                _logger.warning("⚠️ Color vacío o inválido, se omite.")
                continue
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })
            color_values.append(color_val.id)

            for size_data in color_data.get('sizes', []):
                size_name = size_data.get('size')
                if not size_name:
                    continue
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attr.id
                    })
                size_values.append(size_val.id)

        if color_values:
            attribute_lines.append((0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, color_values)]
            }))

        if size_values:
            attribute_lines.append((0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, size_values)]
            }))

        if attribute_lines:
            product_template.write({'attribute_line_ids': attribute_lines})
            _logger.info("✅ Atributos y variantes asignados correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron atributos válidos para asignar.")

        # Imagen principal
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = self.get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🖼 Imagen principal asignada desde: {img_url}")
                    break

        # Imagen por variante (por color)
        for variant in product_template.product_variant_ids:
            variant_color_name = ''
            for value in variant.product_template_attribute_value_ids:
                if value.attribute_id.id == color_attr.id:
                    variant_color_name = value.name
            if variant_color_name:
                color_info = next((c for c in data.get('colors', []) if c.get('colors', {}).get('es') == variant_color_name), None)
                if color_info:
                    variant_images = color_info.get('images', [])
                    for v_img in variant_images:
                        img_url = v_img.get("url_image", "")
                        if img_url:
                            image_bin = self.get_image_binary_from_url(img_url)
                            if image_bin:
                                variant.image_1920 = image_bin
                                _logger.info(f"🖼 Imagen asignada a variante: {variant.name}")
                                break

        _logger.info("🎯 Proceso finalizado correctamente para NS300.")