import json
import base64
import requests
from io import BytesIO
from PIL import Image
from odoo import models, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # BLOQUE 1 - Cargar parámetros
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([proxy_url, username, password, api_key]):
            raise UserError("Faltan parámetros en la configuración del sistema")

        catalog_reference = "NS300"

        # BLOQUE 2 - Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip"
        }
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando con TopTex: {auth_response.status_code}")
        token = auth_response.json().get("token")

        # BLOQUE 3 - Llamada a producto por catalog_reference
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        product_headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/json"
        }
        product_response = requests.get(product_url, headers=product_headers)
        _logger.info(f"🔍 Llamada a producto: {product_url} | Status: {product_response.status_code}")

        if product_response.status_code != 200:
            raise UserError(f"Error al obtener producto: {product_response.status_code}")

        data = product_response.json()
        if not isinstance(data, dict) or not data.get("products"):
            raise UserError("No se ha recibido un JSON válido con productos.")

        product = data["products"][0]
        _logger.info(f"📦 Producto recibido: {json.dumps(product, indent=2)}")

        # BLOQUE 4 - Mapper base
        name = product.get("translatedName", {}).get("es", product.get("designation", "Sin nombre"))
        description = product.get("description", {}).get("es", "")
        brand_name = product.get("brand", {}).get("name", "Sin marca")
        reference = product.get("catalogReference", "")
        main_image_url = product.get("images", [{}])[0].get("url", "")
        type = "consu"
        categ_id = self.env.ref("product.product_category_all").id

        # BLOQUE 5 - Obtener precio de coste
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_reference}"
        price_response = requests.get(price_url, headers=product_headers)
        price = 0.0
        if price_response.status_code == 200:
            try:
                price_data = price_response.json()
                price = price_data["variants"][0]["purchasePrice"]["amount"]
            except Exception as e:
                _logger.warning(f"No se pudo obtener precio: {str(e)}")
        else:
            _logger.warning(f"Error en precio (status {price_response.status_code})")

        # BLOQUE 6 - Obtener stock
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_reference}"
        stock_response = requests.get(stock_url, headers=product_headers)
        stock = 0
        if stock_response.status_code == 200:
            try:
                stock_data = stock_response.json()
                for variant in stock_data.get("variants", []):
                    stock += int(variant.get("stock", 0))
            except Exception as e:
                _logger.warning(f"No se pudo obtener stock: {str(e)}")
        else:
            _logger.warning(f"Error en stock (status {stock_response.status_code})")

        # BLOQUE 7 - Crear marca
        brand_id = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
        if not brand_id:
            brand_id = self.env['product.brand'].create({'name': brand_name})

        # BLOQUE 8 - Imagen principal
        image_1920 = False
        if main_image_url:
            try:
                image_response = requests.get(main_image_url)
                if image_response.status_code == 200:
                    image = Image.open(BytesIO(image_response.content))
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    image_1920 = base64.b64encode(buffer.getvalue())
            except Exception as e:
                _logger.warning(f"No se pudo procesar la imagen principal: {str(e)}")

        # BLOQUE 9 - Crear atributos y valores
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        attribute_lines = []
        variant_images = {}

        for color in product.get("colors", []):
            color_name = color.get("translatedName", {}).get("es", "")
            color_value = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_value:
                color_value = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })

            if color_name not in variant_images and color.get("images"):
                img_url = color["images"][0].get("url", "")
                if img_url:
                    try:
                        img_resp = requests.get(img_url)
                        if img_resp.status_code == 200:
                            img = Image.open(BytesIO(img_resp.content))
                            buff = BytesIO()
                            img.save(buff, format="PNG")
                            variant_images[color_value.id] = base64.b64encode(buff.getvalue())
                    except Exception as e:
                        _logger.warning(f"No se pudo procesar imagen de color {color_name}: {str(e)}")

        for size in product.get("sizes", []):
            size_name = size.get("translatedName", {}).get("es", "")
            size_value = self.env['product.attribute.value'].search([
                ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
            ], limit=1)
            if not size_value:
                size_value = self.env['product.attribute.value'].create({
                    'name': size_name,
                    'attribute_id': size_attr.id
                })

        # BLOQUE 10 - Crear el product.template
        template_vals = {
            'name': name,
            'default_code': reference,
            'type': type,
            'categ_id': categ_id,
            'standard_price': price,
            'description_sale': description,
            'image_1920': image_1920,
            'qty_available': stock,
            'product_brand_id': brand_id.id,
            'attribute_line_ids': [
                (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_attr.value_ids.ids)]}),
                (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_attr.value_ids.ids)]}),
            ]
        }

        template = self.env['product.template'].create(template_vals)

        # BLOQUE 11 - Asignar imágenes por variante
        for variant in template.product_variant_ids:
            for color_val_id, img_b64 in variant_images.items():
                if color_val_id in variant.product_template_attribute_value_ids.mapped('product_attribute_value_id').ids:
                    variant.image_1920 = img_b64

        _logger.info(f"✅ Producto {catalog_reference} creado correctamente con {len(template.product_variant_ids)} variantes.")
        return True