import requests
import logging
import json
from odoo import models, api, fields
from odoo.exceptions import UserError
from PIL import Image
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros de configuración.")

        # 1️⃣ Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {'username': username, 'password': password}
        auth_headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get('token')
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # 2️⃣ Descarga del producto NS300
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"📥 Respuesta cruda:\n{response.text}")
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
            data_list = response.json()
            data_list = data_list if isinstance(data_list, list) else [data_list]
            if not data_list:
                raise UserError("❌ No se encontró el producto en la respuesta.")
            data = data_list[0]
            _logger.info(f"🟢 JSON interpretado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error obteniendo el producto desde API: {e}")
            return

        # 3️⃣ Mapeo de campos principales
        try:
            brand_data = data.get("brand") or {}
            brand = brand_data.get("name", {}).get("es", "")
            name = data.get("designation", {}).get("es", "Producto sin nombre")
            full_name = f"[{data.get('catalogReference','')}] {name}"
            description = data.get("description", {}).get("es", "")
            default_code = data.get("catalogReference", "NS300")
            list_price = float(data.get("publicUnitPrice", 0) or 0)
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

            template_vals = {
                'name': full_name,
                'default_code': default_code,
                'type': 'consu',
                'description_sale': description,
                'list_price': list_price,
                'standard_price': standard_price,
                'categ_id': self.env.ref('product.product_category_all').id,
            }

            if brand:
                brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
                if not brand_obj:
                    brand_obj = self.env['product.brand'].create({'name': brand})
                template_vals['product_brand_id'] = brand_obj.id

            _logger.info(f"✅ Datos para crear plantilla: {template_vals}")

            product_template = self.create(template_vals)
            _logger.info(f"✅ Plantilla creada: {product_template.name}")

        except Exception as e:
            _logger.error(f"❌ Error en mapeo de datos principales: {e}")
            return

        # 4️⃣ Crear atributos y variantes
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        try:
            for color in data.get("colors", []):
                color_name = color.get("color", {}).get("es", "")
                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
                ], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({
                        'name': color_name, 'attribute_id': color_attr.id
                    })
                color_values.append(color_val.id)

                for size in color.get("sizes", []):
                    size_name = size.get("size", "")
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

            product_template.write({'attribute_line_ids': attribute_lines})
            _logger.info("✅ Variantes y atributos creados correctamente.")

        except Exception as e:
            _logger.error(f"❌ Error creando variantes: {e}")
            return

        # 5️⃣ Imagen principal (Pillow)
        try:
            images = data.get("images", [])
            img_url = ""
            for img in images:
                img_url = img.get("url_image", "")
                if img_url:
                    break
            if img_url:
                img_bin = self.get_image_binary_from_url(img_url)
                if img_bin:
                    product_template.image_1920 = img_bin
                    _logger.info("✅ Imagen principal asignada.")
        except Exception as e:
            _logger.error(f"❌ Error asignando imagen principal: {e}")

        # 6️⃣ Imagen por variante de color (Pillow)
        try:
            for variant in product_template.product_variant_ids:
                color_value = variant.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.id == color_attr.id
                ).name

                color_data = next((c for c in data.get("colors", []) if c.get("color", {}).get("es", "") == color_value), None)
                variant_img = color_data.get("url_image", "") if color_data else None
                if variant_img:
                    img_bin = self.get_image_binary_from_url(variant_img)
                    if img_bin:
                        variant.image_1920 = img_bin
                        _logger.info(f"✅ Imagen asignada a variante: {variant.name}")
        except Exception as e:
            _logger.error(f"❌ Error asignando imagen a variantes: {e}")

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                img_bytes = buffer.getvalue()
                return base64.b64encode(img_bytes)
            else:
                _logger.warning(f"⚠ No se pudo descargar imagen desde {url}")
                return None
        except Exception as e:
            _logger.error(f"❌ Error procesando imagen: {e}")
            return None