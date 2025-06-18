import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            _logger.info(f"✅ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {str(e)}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        response = requests.get(product_url, headers=headers)
        data_list = response.json()
        data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}

        brand = data.get("brand", {}).get("name", {}).get("es", "")
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        template_vals = {
            'name': f"{brand} {name}",
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': 9.8,
            'standard_price': 0,
            'categ_id': self.env.ref("product.product_category_all").id,
        }

        product_template = self.create(template_vals)

        attribute_lines = []

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            color_img = color.get("url_image")

            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1) or self.env['product.attribute.value'].create({
                'name': color_name, 'attribute_id': color_attr.id
            })

            size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].create({'name': 'Talla'})

            size_vals = []
            for size in color.get("sizes", []):
                size_name = size.get("size")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1) or self.env['product.attribute.value'].create({
                    'name': size_name, 'attribute_id': size_attr.id
                })
                size_vals.append(size_val.id)

            attribute_lines.extend([
                {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [color_val.id])]},
                {'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_vals)]}
            ])

        product_template.write({
            'attribute_line_ids': [(0, 0, line) for line in attribute_lines]
        })

        main_img = data.get("images", [{}])[0].get("url_image", "")
        if main_img:
            product_template.image_1920 = get_image_binary_from_url(main_img)

        for variant in product_template.product_variant_ids:
            variant_color = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name == "Color"
            ).name
            color_data = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es") == variant_color), {})
            variant_img = color_data.get("url_image")
            if variant_img:
                variant.image_1920 = get_image_binary_from_url(variant_img)