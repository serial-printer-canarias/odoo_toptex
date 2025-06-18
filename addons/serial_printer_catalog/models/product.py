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

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("🔐 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
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
            data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
            _logger.info(f"📦 JSON interpretado:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde API: {e}")
            return

        brand_data = data.get("brand") or {}
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", {}).get("es", "")
        else:
            brand = ""

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = 9.8
        standard_price = 0.0

        # Obtener precio de coste real
        try:
            price_url = f"{proxy_url}/v3/products/price"
            price_payload = {"catalog_reference": default_code}
            price_headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "Content-Type": "application/json"
            }
            price_response = requests.post(price_url, json=price_payload, headers=price_headers)
            if price_response.status_code == 200:
                price_data = price_response.json()
                standard_price = float(price_data.get("wholesalePrice", "0").replace(",", "."))
                _logger.info(f"💰 Precio de coste obtenido: {standard_price}")
            else:
                _logger.warning(f"⚠️ No se pudo obtener el precio de coste: {price_response.text}")
        except Exception as e:
            _logger.warning(f"❌ Error al obtener precio de coste: {str(e)}")

        # Obtener stock real
        try:
            stock_url = f"{proxy_url}/v3/products/inventory"
            stock_payload = {"catalog_reference": default_code}
            stock_headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "Content-Type": "application/json"
            }
            stock_response = requests.post(stock_url, json=stock_payload, headers=stock_headers)
            if stock_response.status_code == 200:
                stock_data = stock_response.json()
                total_stock = stock_data.get("totalStock", 0)
                _logger.info(f"📦 Stock total obtenido: {total_stock}")
            else:
                _logger.warning(f"⚠️ No se pudo obtener el stock: {stock_response.text}")
        except Exception as e:
            _logger.warning(f"❌ Error al obtener stock: {str(e)}")

        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }

        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Atributos y variantes
        attribute_lines = []

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            for size in color.get("sizes", []):
                size_name = size.get("size")

                color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
                if not color_attr:
                    color_attr = self.env['product.attribute'].create({'name': 'Color'})
                color_val = self.env['product.attribute.value'].search([
                    ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
                ], limit=1)
                if not color_val:
                    color_val = self.env['product.attribute.value'].create({
                        'name': color_name, 'attribute_id': color_attr.id
                    })

                size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
                if not size_attr:
                    size_attr = self.env['product.attribute'].create({'name': 'Talla'})
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': size_attr.id
                    })

                if color_attr and color_val and all(line['attribute_id'] != color_attr.id for line in attribute_lines):
                    attribute_lines.append({
                        'attribute_id': color_attr.id,
                        'value_ids': [(6, 0, [color_val.id])]
                    })

                if size_attr and size_val and all(line['attribute_id'] != size_attr.id for line in attribute_lines):
                    attribute_lines.append({
                        'attribute_id': size_attr.id,
                        'value_ids': [(6, 0, [size_val.id])]
                    })

        if attribute_lines:
            product_template.write({
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines]
            })
            _logger.info("✅ Atributos y valores asignados correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron atributos para asignar.")

        # Imagen principal (Pillow)
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                    break

        # Imagen por variante de color (Pillow)
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name == "Color"
            ).name
            color_data = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color_value), None)
            variant_img = color_data.get("url_image") if color_data else None
            if variant_img:
                image_bin = get_image_binary_from_url(variant_img)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")