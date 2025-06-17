import requests
import json
import base64
from io import BytesIO
from PIL import Image
from odoo import models
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise ValueError("❌ Faltan credenciales o parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise ValueError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise ValueError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Petición de producto (con catalog_reference)
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token,
            'Accept-Encoding': 'gzip, deflate, br'
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"🔎 URL de producto: {product_url}")
            _logger.info(f"🔎 Headers de producto: {headers}")
            _logger.info(f"🔎 Respuesta cruda:\n{response.text}")
            if response.status_code != 200:
                raise ValueError(f"❌ Error en llamada de producto: {response.status_code}")
            data = response.json()
            if isinstance(data, list):
                data = data[0]
            _logger.info(f"🟢 JSON interpretado:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error obteniendo producto: {e}")
            return

        try:
            # Mapper
            translated_name = data.get("translatedName", {}).get("es", "Producto sin nombre")
            brand_data = data.get("brand")
            marca = brand_data.get("name", {}).get("es") if brand_data else "Sin Marca"
            description = data.get("description", {}).get("es", "")
            reference = data.get("catalogReference", "SIN_REF")

            # Precio de venta
            sale_prices = data.get("salePrices", [])
            list_price = sale_prices[0].get("price", 0.0) if sale_prices else 0.0

            # Precio de coste (usamos purchasePrices)
            purchase_prices = data.get("purchasePrices", [])
            standard_price = purchase_prices[0].get("price", 0.0) if purchase_prices else 0.0

            _logger.info(f"📦 Nombre: {translated_name}, Marca: {marca}, Precio venta: {list_price}, Precio coste: {standard_price}")

            # Buscar o crear categoría (opcional: la mantenemos simple)
            categ_id = self.env['product.category'].search([('name', '=', 'TopTex')], limit=1)
            if not categ_id:
                categ_id = self.env['product.category'].create({'name': 'TopTex'})

            # Crear atributos (Color y Talla)
            attribute_obj = self.env['product.attribute']
            color_attribute = attribute_obj.search([('name', '=', 'Color')], limit=1)
            if not color_attribute:
                color_attribute = attribute_obj.create({'name': 'Color'})

            size_attribute = attribute_obj.search([('name', '=', 'Talla')], limit=1)
            if not size_attribute:
                size_attribute = attribute_obj.create({'name': 'Talla'})

            # Imágenes principales
            image_url = data.get("images", {}).get("front", "")
            image_1920 = False
            if image_url:
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        img = Image.open(BytesIO(image_response.content))
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        image_1920 = base64.b64encode(buffer.getvalue())
                except Exception as e_img:
                    _logger.warning(f"⚠️ No se pudo procesar la imagen principal: {e_img}")

            # Crear el producto template
            product_tmpl = self.env['product.template'].create({
                'name': translated_name,
                'default_code': reference,
                'list_price': list_price,
                'standard_price': standard_price,
                'categ_id': categ_id.id,
                'type': 'product',
                'description_sale': description,
                'image_1920': image_1920,
            })
            _logger.info("✅ Producto template creado correctamente.")

            # Variantes de color y talla
            for color in data.get("colors", []):
                color_name = color.get("translatedName", {}).get("es", "")
                # Crear valor de atributo Color si no existe
                color_value = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attribute.id)
                ], limit=1)
                if not color_value:
                    color_value = self.env['product.attribute.value'].create({
                        'name': color_name,
                        'attribute_id': color_attribute.id
                    })

                for size in color.get("sizes", []):
                    size_name = size.get("sizeName", "")
                    size_value = self.env['product.attribute.value'].search([
                        ('name', '=', size_name), ('attribute_id', '=', size_attribute.id)
                    ], limit=1)
                    if not size_value:
                        size_value = self.env['product.attribute.value'].create({
                            'name': size_name,
                            'attribute_id': size_attribute.id
                        })

                    # Crear variante
                    variant = self.env['product.product'].create({
                        'product_tmpl_id': product_tmpl.id,
                        'attribute_value_ids': [(6, 0, [color_value.id, size_value.id])]
                    })
                    _logger.info(f"🟢 Variante creada: Color {color_name} - Talla {size_name}")

            _logger.info("✅ Sincronización finalizada correctamente.")

        except Exception as e:
            _logger.error(f"❌ Error procesando producto: {e}")