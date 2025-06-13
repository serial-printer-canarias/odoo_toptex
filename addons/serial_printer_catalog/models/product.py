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
        # Leer parámetros desde Odoo
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        headers_auth = {"x-api-key": api_key, "Content-Type": "application/json"}
        payload_auth = {"username": username, "password": password}
        response_auth = requests.post(auth_url, headers=headers_auth, json=payload_auth)
        response_auth.raise_for_status()
        token = response_auth.json().get("token")
        _logger.info(f"✅ Token recibido correctamente")

        # Consulta del producto NS300 completo
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        _logger.info(f"✅ JSON interpretado correctamente: {json.dumps(data, indent=2)}")

        # Procesar solo el primer producto (único) de NS300
        product_data = data[0] if isinstance(data, list) and data else {}
        if not product_data:
            _logger.error("❌ No se encontró el producto en la respuesta.")
            return

        # Mapear campos principales
        name = product_data.get("designation", {}).get("es", "Producto sin nombre")
        brand_data = product_data.get("brand", {})
        brand = brand_data.get("name", {}).get("es", "") if brand_data else ""

        description = product_data.get("description", {}).get("es", "")
        default_code = product_data.get("catalogReference", "NS300")
        list_price = product_data.get("publicPrice", 0)

        # Obtener primer precio coste encontrado
        standard_price = 0
        for color in product_data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    standard_price = float(price_str)
                    break
                except:
                    continue
            if standard_price:
                break

        # Crear plantilla
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }
        _logger.info(f"✅ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Crear atributos de Color y Talla
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # Crear valores de atributos
        for color in product_data.get("colors", []):
            color_name = color.get("color", {}).get("es")
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

            for size in color.get("sizes", []):
                size_name = size.get("size")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attr.id
                    })

                # Crear combinación
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
            _logger.info("✅ Variantes asignadas correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron atributos válidos.")

        # Asignar imagen principal
        images = product_data.get("images", [])
        for img in images:
            img_url = img.get("url_packshot")
            if img_url:
                img_bin = self.get_image_binary_from_url(img_url)
                if img_bin:
                    product_template.image_1920 = img_bin
                    _logger.info(f"✅ Imagen principal asignada desde {img_url}")
                break

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue())
            return img_str
        except Exception as e:
            _logger.warning(f"⚠️ Error al descargar imagen: {e}")
            return None