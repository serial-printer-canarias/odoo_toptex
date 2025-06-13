import requests
import json
import base64
import logging
from io import BytesIO
from PIL import Image
from odoo import models, fields, api
from odoo.exceptions import UserError

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
            raise UserError("❌ Faltan credenciales o parámetros de configuración")

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {'username': username, 'password': password}
        auth_headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Obtener el producto completo (All Products)
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"📦 Respuesta cruda:\n{response.text}")
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
            data_list = response.json()
            data = data_list[0] if isinstance(data_list, list) else data_list
            _logger.info(f"🟢 JSON interpretado:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde API: {e}")
            return

        # Procesar datos
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("productReference", "NS300")
        list_price = float(data.get("publicUnitPrice", 0.0))
        standard_price = 0.0

        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    standard_price = float(price_str)
                    break
                except Exception:
                    continue
            if standard_price:
                break

        # Crear plantilla principal
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }
        _logger.info(f"🟢 Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Crear atributos y variantes
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        for color in data.get("colors", []):
            color_name = color.get("color", {}).get("es")
            for size in color.get("sizes", []):
                size_name = size.get("size")

                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({
                        'name': color_name, 'attribute_id': color_attr.id
                    })

                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': size_attr.id
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
                img_bin = self.get_image_binary_from_url(img_url)
                if img_bin:
                    product_template.image_1920 = img_bin
                    _logger.info(f"✅ Imagen principal asignada desde: {img_url}")
                break

        # Imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.id == color_attr.id).name

            color_data = next((c for c in data.get("colors", []) if c.get("color", {}).get("es") == color_value), None)
            variant_img = color_data.get("url_image", "") if color_data else None

            if variant_img:
                img_bin = self.get_image_binary_from_url(variant_img)
                if img_bin:
                    variant.image_variant_1920 = img_bin
                    _logger.info(f"🖼 Imagen asignada a variante: {variant.name}")

    def get_image_binary_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("image"):
                img = Image.open(BytesIO(response.content))
                img = img.convert("RGB")
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue())
            else:
                _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
                return None
        except Exception as e:
            _logger.warning(f"❌ Error al procesar imagen desde URL {url}: {e}")
            return None