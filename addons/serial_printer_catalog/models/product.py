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

        # 1. Obtener token de autenticación
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

        # 2. Llamada a producto NS300
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

        # 3. Parsear campos principales
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # 4. Precio de venta (list_price) y de coste (standard_price)
        list_price = 0.0
        standard_price = 0.0

        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    list_price = float(price_str)
                    standard_price = float(size.get("purchasePrice", price_str).replace(",", "."))
                    break
                except Exception:
                    continue
            if list_price:
                break

        # 5. Stock total (sumar por variante si existe)
        total_stock = 0
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                try:
                    total_stock += int(size.get("stock", 0))
                except Exception:
                    continue

        _logger.info(f"💰 Precio de coste obtenido: {standard_price}")
        _logger.info(f"💸 Precio de venta obtenido: {list_price}")
        _logger.info(f"📦 Stock total obtenido: {total_stock}")

        # 6. Crear plantilla de producto
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'product',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        }

        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # 7. Atributos y variantes (Color y Talla)
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
            color_name = color.get("colors", {}).get("es", "")
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
                if size_val.id not in size_values:
                    size_values.append(size_val.id)

        attribute_lines.append({
            'attribute_id': color_attr.id,
            'value_ids': [(6, 0, color_values)]
        })
        attribute_lines.append({
            'attribute_id': size_attr.id,
            'value_ids': [(6, 0, size_values)]
        })

        if attribute_lines:
            product_template.write({
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines]
            })
            _logger.info("✅ Atributos y valores asignados correctamente.")
        else:
            _logger.warning("⚠️ No se encontraron atributos para asignar.")

        # 8. Imagen principal
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                    break

        # 9. Imagen por variante de color (solo si hay variantes creadas)
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

        # 10. LOG STOCK en logger
        _logger.info(f"📦 Stock total aplicado (informativo): {total_stock}")

        # 11. Finalización
        _logger.info("🎉 Producto NS300 sincronizado correctamente con todas las variantes, imágenes y precios.")