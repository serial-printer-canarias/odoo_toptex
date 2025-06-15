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
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Obtener el token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = { "username": username, "password": password }
        auth_headers = { "x-api-key": api_key, "Content-Type": "application/json" }
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        token = auth_response.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        # Descargar el producto NS300 desde API
        catalog_reference = "ns300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"❌ Error al obtener producto: {response.text}")
            return

        data_list = response.json()
        if isinstance(data_list, list):
            data = data_list[0]
        else:
            data = data_list.get("data", {})

        _logger.info("✅ JSON interpretado correctamente.")
        _logger.info(json.dumps(data, indent=2))

        # Obtener precio coste desde endpoint precio
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_reference}"
        price_response = requests.get(price_url, headers=headers)
        price_data = price_response.json()
        try:
            standard_price = float(price_data[0]["colors"][0]["sizes"][0]["wholesalePrice"]["value"])
        except:
            standard_price = 0.0
            _logger.warning("⚠️ No se pudo obtener precio de coste.")

        # Obtener stock desde endpoint inventario
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_reference}"
        stock_response = requests.get(stock_url, headers=headers)
        stock_data = stock_response.json()
        total_stock = 0
        try:
            for color in stock_data[0].get("colors", []):
                for size in color.get("sizes", []):
                    total_stock += int(size.get("stock", {}).get("quantity", 0))
        except:
            _logger.warning("⚠️ No se pudo obtener stock.")

        # Datos generales del producto
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # Marca
        brand_data = data.get("brand", {})
        brand = brand_data.get("name", {}).get("es", "Sin Marca")
        brand_category = self.env['product.category'].search([('name', '=', brand)], limit=1)
        if not brand_category:
            brand_category = self.env['product.category'].create({'name': brand})

        # Precio venta
        list_price = data.get("publicUnitPrice", 0.0)

        # Imagen principal
        image_url = ""
        images = data.get("images", [])
        for img in images:
            image_url = img.get("url_packshot")
            if image_url:
                break

        image_bin = False
        if image_url:
            try:
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                image_bin = base64.b64encode(buffer.getvalue())
            except Exception as e:
                _logger.warning(f"No se pudo procesar la imagen principal: {str(e)}")

        # Crear plantilla del producto
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': brand_category.id,
            'image_1920': image_bin or False,
            'qty_available': total_stock
        }

        product_template = self.create(template_vals)
        _logger.info(f"✅ Producto creado: {product_template.name}")

        # Crear atributos y variantes
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es", "").strip()
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
            _logger.info("✅ Atributos y variantes creados correctamente.")

        # Asignar imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.id == color_attr.id
            )
            color_name_variant = color_value.name if color_value else None

            color_data_match = next(
                (c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color_name_variant), None)

            if color_data_match:
                images = color_data_match.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = self.get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                            _logger.info(f"✅ Imagen asignada a variante {variant.name} desde {img_url}")
                        break

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                return base64.b64encode(buffer.getvalue())
        except Exception as e:
            _logger.warning(f"Error procesando imagen de variante: {str(e)}")
        return False