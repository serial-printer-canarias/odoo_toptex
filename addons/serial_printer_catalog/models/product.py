import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"📥 Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            image = Image.open(io.BytesIO(response.content))
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
            _logger.info(f"✅ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
            return None
    except Exception as e:
        _logger.warning(f"⚠️ Error al procesar imagen desde {url}: {e}")
        return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        self.env.cr.commit()
        _logger.info("🚀 Iniciando sincronización con TopTex...")

        try:
            username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
            password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
            api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
            proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
            if not all([username, password, api_key, proxy_url]):
                raise ValueError("❌ Faltan parámetros de configuración")

            # Autenticación
            auth_url = f"{proxy_url}/v3/authenticate"
            auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            payload = {"username": username, "password": password}
            auth_response = requests.post(auth_url, json=payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise ValueError(f"❌ Error autenticando: {auth_response.status_code} {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise ValueError("❌ No se recibió token válido")

            _logger.info("🔐 Token recibido correctamente")

            catalog_reference = "NS300"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "Accept-Encoding": "gzip, deflate, br"
            }

            # Llamada principal de producto
            product_url = f"{proxy_url}/v3/products?catalog_references={catalog_reference}&usage_right=b2b_b2c"
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"❌ Error obteniendo producto: {response.status_code} {response.text}")
            data_list = response.json().get("data", [])
            if not data_list:
                raise ValueError("❌ No se obtuvo ningún producto desde la API.")

            product = data_list[0]  # NS300 único

            # Llamada de stock
            stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_reference}"
            stock_response = requests.get(stock_url, headers=headers)
            stock_qty = 0
            if stock_response.status_code == 200:
                stock_data = stock_response.json()
                for stock_entry in stock_data:
                    if stock_entry.get("id") == "toptex":
                        stock_qty = stock_entry.get("stock", 0)
            else:
                _logger.warning("⚠️ No se pudo obtener el stock")

            # Llamada de precio
            price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_reference}"
            price_response = requests.get(price_url, headers=headers)
            standard_price = 0.0
            if price_response.status_code == 200:
                price_data = price_response.json()
                price_items = price_data.get("products", [])
                if price_items:
                    prices = price_items[0].get("prices", [])
                    for p in prices:
                        if p.get("quantity") == 1:
                            standard_price = float(p.get("price", 0))
            else:
                _logger.warning("⚠️ No se pudo obtener el precio de coste")

            # Mapeo de campos principales
            name = product.get("translatedName", {}).get("es", "Producto sin nombre")
            description = product.get("description", {}).get("es", "")
            brand_data = product.get("brand")
            brand = brand_data.get("name", {}).get("es") if brand_data else "Sin marca"

            template_vals = {
                'name': f"{name} - {brand}",
                'default_code': catalog_reference,
                'type': 'consu',
                'categ_id': self.env.ref('product.product_category_all').id,
                'list_price': standard_price * 2,  # Por ejemplo: margen x2
                'standard_price': standard_price,
                'description_sale': description,
                'qty_available': stock_qty
            }

            _logger.info(f"📦 Datos para crear plantilla: {template_vals}")
            product_template = self.create(template_vals)
            _logger.info(f"✅ Plantilla creada: {product_template.name}")

            # Atributos variantes (colores y tallas)
            attribute_lines = []
            colors = product.get("colors", [])
            sizes = product.get("sizes", [])

            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})

            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

            for color in colors:
                color_name = color.get("translatedColorName", {}).get("es", "Sin color")
                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attr.id})

                for size in sizes:
                    size_name = size.get("size", "Única")
                    size_val = self.env['product.attribute.value'].search([
                        ('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1)
                    if not size_val:
                        size_val = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attr.id})

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
                _logger.info("✅ Variantes creadas correctamente.")

            # Imagen principal
            images = product.get("images", [])
            if images:
                main_image_url = images[0].get("url")
                if main_image_url:
                    img_bin = get_image_binary_from_url(main_image_url)
                    if img_bin:
                        product_template.image_1920 = img_bin
                        _logger.info(f"✅ Imagen principal cargada desde {main_image_url}")

            # Imágenes por variantes de color
            for color in colors:
                variant_image_url = color.get("images", [{}])[0].get("url")
                color_name = color.get("translatedColorName", {}).get("es", "Sin color")
                variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('attribute_value_ids.name', '=', color_name)
                ], limit=1)
                if variant and variant_image_url:
                    img_variant_bin = get_image_binary_from_url(variant_image_url)
                    if img_variant_bin:
                        variant.image_1920 = img_variant_bin
                        _logger.info(f"🎯 Imagen variante asignada a {color_name}")

            _logger.info("🚀 Sincronización terminada correctamente.")

        except Exception as e:
            _logger.error(f"❌ Error en sincronización: {str(e)}")