import requests
import json
import base64
import logging
from odoo import models
from PIL import Image
from io import BytesIO

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Autenticación y obtención del token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise Exception(f"Error autenticación: {auth_response.text}")

        token = auth_response.json().get("token")
        _logger.info(f"Token recibido correctamente.")

        # Petición del producto NS300
        catalog_ref = 'NS300'
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        _logger.info(f"Respuesta cruda: {response.text}")

        if response.status_code != 200:
            raise Exception(f"Error al obtener producto: {response.status_code} - {response.text}")

        data = response.json()
        data = data[0] if isinstance(data, list) and data else {}

        if not data:
            raise Exception("No se encontró el producto en la respuesta.")

        _logger.info("✅ JSON interpretado correctamente.")

        # MAPEO PRINCIPAL
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = data.get("brand", {}).get("name", {}).get("es", "").strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", catalog_ref)

        # Marca
        brand_name = data.get("brand", {}).get("name", {}).get("es", "Sin Marca")
        brand_obj = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
        if not brand_obj:
            brand_obj = self.env['product.brand'].create({'name': brand_name})

        # Precio coste (llamada precio)
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
        price_response = requests.get(price_url, headers=headers)
        price_data = price_response.json()
        standard_price = 0.0
        try:
            standard_price = float(price_data[0]["colors"][0]["sizes"][0]["wholesalePrice"]["value"])
        except:
            _logger.warning("No se pudo obtener el precio de coste.")

        # Stock (llamada inventario)
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        stock_response = requests.get(stock_url, headers=headers)
        stock_data = stock_response.json()
        total_stock = sum(
            int(size.get("stock", {}).get("quantity", 0))
            for color in stock_data[0].get("colors", [])
            for size in color.get("sizes", [])
        )

        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'description_sale': description,
            'list_price': 1.0,  # Precio de venta lo fijamos de momento
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
            'product_brand_id': brand_obj.id,
        }

        product_template = self.create(template_vals)
        _logger.info(f"🟢 Producto plantilla creado: {product_template.name}")

        # ATRIBUTOS Y VARIANTES
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            if color_name:
                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
                ], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({
                        'name': color_name, 'attribute_id': color_attr.id
                    })
                color_values.append(color_val.id)

                for size in color.get("sizes", []):
                    size_name = size.get("size")
                    if size_name:
                        size_val = self.env['product.attribute.value'].search([
                            ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                        ], limit=1)
                        if not size_val:
                            size_val = self.env['product.attribute.value'].create({
                                'name': size_name, 'attribute_id': size_attr.id
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
            _logger.info("✅ Variantes creadas correctamente.")

        # IMAGEN PRINCIPAL
        try:
            images = data.get("images", [])
            for img in images:
                url_packshot = img.get("url_packshot")
                if url_packshot:
                    img_bin = self.get_image_binary_from_url(url_packshot)
                    if img_bin:
                        product_template.image_1920 = img_bin
                        _logger.info("✅ Imagen principal asignada.")
                    break
        except Exception as e:
            _logger.warning(f"No se pudo cargar imagen principal: {e}")

        # IMÁGENES POR VARIANTE (simplificado por ahora, se puede detallar más adelante)
        for variant in product_template.product_variant_ids:
            _logger.info(f"Preparado para asignar imagen por variante: {variant.name}")

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                output = BytesIO()
                image.save(output, format='PNG')
                return base64.b64encode(output.getvalue())
        except Exception as e:
            _logger.warning(f"Error al procesar imagen desde URL: {url} - {str(e)}")
        return False