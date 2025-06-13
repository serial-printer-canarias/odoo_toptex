import json
import requests
import logging
import base64
from io import BytesIO
from PIL import Image
from odoo import models, api
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
            raise UserError("❌ Faltan credenciales o parámetros de configuración.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {'username': username, 'password': password}
        auth_headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            auth_response.raise_for_status()
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió token.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            raise UserError(f"❌ Error autenticando: {e}")

        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            data_list = response.json()
            data = data_list[0] if isinstance(data_list, list) else data_list
            _logger.info(f"🟢 JSON recibido:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            raise UserError(f"❌ Error obteniendo producto: {e}")

        # Datos principales
        brand = data.get("brandName", {}).get("es", "")
        name = data.get("translatedName", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("productReference", catalog_reference)
        list_price = float(data.get("publicUnitPrice", 0))
        standard_price = 0.0  # lo calcularemos después

        # Plantilla base
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref('product.product_category_all').id,
        }
        _logger.info(f"✅ Datos plantilla: {template_vals}")
        product_template = self.create(template_vals)

        # Atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es", "")
            if not color_name:
                continue

            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name, 'attribute_id': color_attr.id
                })
            if color_val.id not in color_values:
                color_values.append(color_val.id)

            for size in color.get("sizes", []):
                size_name = size.get("size", "")
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    price_float = float(price_str)
                    if standard_price == 0.0:
                        standard_price = price_float
                except:
                    price_float = 0.0

                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': size_attr.id
                    })
                if size_val.id not in size_values:
                    size_values.append(size_val.id)

        # Aplicar variantes
        product_template.write({
            'standard_price': standard_price,
            'attribute_line_ids': [
                (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_values)]}),
                (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_values)]}),
            ]
        })
        _logger.info("✅ Variantes generadas correctamente.")

        # Imagen principal
        try:
            img_url = data.get("packshotUrl", "")
            if img_url:
                img_bin = self.download_image(img_url)
                if img_bin:
                    product_template.image_1920 = img_bin
                    _logger.info(f"✅ Imagen principal asignada: {img_url}")
        except Exception as e:
            _logger.warning(f"⚠ Error imagen principal: {e}")

        # Imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == color_attr).name
            color_data = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es", "") == color_value), None)
            if color_data:
                variant_img_url = color_data.get("urlPackshot", "")
                if variant_img_url:
                    img_bin = self.download_image(variant_img_url)
                    if img_bin:
                        variant.image_variant_1920 = img_bin
                        _logger.info(f"✅ Imagen asignada a variante {variant.display_name}")

    def download_image(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                img = Image.open(BytesIO(response.content))
                img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                return base64.b64encode(buffer.getvalue())
        except Exception as e:
            _logger.warning(f"⚠ Error descargando imagen: {e}")
        return None