import requests
import json
import logging
import base64
from io import BytesIO
from PIL import Image
from odoo import models
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros desde el sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        api_key = ir_config.get_param('toptex_api_key')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        # Obtener token
        token_url = f"{proxy_url}/v3/authenticate"
        headers_token = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "username": username,
            "password": password
        }
        response_token = requests.post(token_url, headers=headers_token, json=payload)
        if response_token.status_code != 200:
            raise Exception(f"Error autenticando: {response_token.text}")
        token = response_token.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        # Obtener datos del producto NS300
        catalog_reference = "ns300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers_product = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers_product)
        _logger.info(f"🔗 URL consultada: {product_url}")
        if response.status_code != 200:
            raise Exception(f"Error al obtener producto: {response.text}")
        data_list = response.json()
        _logger.info("✅ JSON interpretado correctamente.")

        if not data_list or not isinstance(data_list, list):
            _logger.error("❌ No se encontró el producto en la respuesta.")
            return

        data = data_list[0]  # Cogemos el primer resultado

        # Mapeo de datos principales
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = data.get("brand", {}).get("name", {}).get("es", "") + " " + name
        full_name = full_name.strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = data.get("publicUnitPrice", 0.0)

        # Precio de coste (primer price válido)
        standard_price = 0.0
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    standard_price = float(price_str)
                    break
                except:
                    continue
            if standard_price:
                break

        _logger.info(f"📦 Producto: {full_name} / Venta: {list_price} / Coste: {standard_price}")

        # Crear plantilla
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }
        _logger.info(f"📝 Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Atributos: Color y Talla
        attribute_lines = []

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_value_map = {}

        for color in data.get("colors", []):
            color_name = color.get("color", {}).get("es", "").strip()
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

            color_value_map[color_name] = color_val.id

            for size in color.get("sizes", []):
                size_name = size.get("size", "").strip()
                if not size_name:
                    _logger.warning("⚠️ Talla vacía o inválida, se omite.")
                    continue

                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
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
            _logger.info("✅ Atributos y variantes asignados correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron atributos para asignar.")

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

        # Imágenes por variante (color)
        for variant in product_template.product_variant_ids:
            variant_color_name = variant.attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id).name
            variant_color_data = next(
                (c for c in data.get("colors", []) if c.get("color", {}).get("es", "") == variant_color_name),
                None
            )
            if variant_color_data:
                images_variant = variant_color_data.get("images", [])
                for img in images_variant:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = self.get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_variant_1920 = image_bin
                            _logger.info(f"🖼 Imagen asignada a variante: {variant.name}")
                        break

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200 and response.headers['Content-Type'].startswith("image/"):
                image = Image.open(BytesIO(response.content))
                image = image.convert("RGB")
                output = BytesIO()
                image.save(output, format='PNG')
                return base64.b64encode(output.getvalue())
            else:
                _logger.warning(f"⚠️ Error al descargar imagen o tipo inválido: {url}")
                return False
        except Exception as e:
            _logger.warning(f"⚠️ Excepción al procesar imagen: {str(e)}")
            return False