import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"Descargando imagen: {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
        else:
            _logger.warning(f"Contenido no válido como imagen: {url}")
    except Exception as e:
        _logger.warning(f"Error al procesar imagen {url}: {str(e)}")
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

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("Token recibido correctamente.")

        # 2. Descarga del producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        _logger.info(f"Respuesta cruda:\n{response.text}")
        if response.status_code != 200:
            raise UserError(f"Error al obtener producto: {response.status_code} - {response.text}")
        data_list = response.json()
        data = data_list[0] if isinstance(data_list, list) and data_list else data_list

        _logger.info(f"JSON interpretado:\n{json.dumps(data, indent=2)[:1500]}")  # Solo los primeros 1500 chars

        # 3. Información básica
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
        full_name = f"{brand} {name}".strip() if brand else name

        # 4. Precios y stock
        # Precio de coste por variante (si existe), si no, buscar en el color principal
        standard_price = 0.0
        list_price = 0.0
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                try:
                    standard_price = float(size.get("wholesaleUnitPrice", "0").replace(",", "."))
                    list_price = float(size.get("publicUnitPrice", "0").replace(",", "."))
                    break
                except Exception:
                    continue
            if standard_price and list_price:
                break
        # Stock: sumar todos los availableStock de todas las variantes si existe en JSON
        stock = 0
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                stock += int(size.get("stock", 0))

        # 5. Imagen principal (la del producto)
        image_bin = None
        images = data.get("images", [])
        image_url = ""
        if images:
            # Pilla el primer packshot que encuentres
            for img in images:
                image_url = img.get("url_packshot") or img.get("url_image") or ""
                if image_url:
                    break
        if image_url:
            image_bin = get_image_binary_from_url(image_url)

        # 6. Crear el producto en Odoo (PLANTILLA)
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'image_1920': image_bin or False,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref("product.product_category_all").id,
            'detailed_type': 'consu',
        }
        _logger.info(f"Datos plantilla: {template_vals}")

        product_template = self.create(template_vals)
        _logger.info(f"Plantilla creada: {product_template.name}")

        # 7. Atributos y variantes (color/talla)
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_val_map = {}
        size_val_map = {}
        attribute_lines = []

        # Creamos todos los valores necesarios para las variantes
        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es") or color.get("colorReference", "")
            if not color_name:
                continue
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attr.id})
            color_val_map[color_name] = color_val.id

            for size in color.get("sizes", []):
                size_name = size.get("size")
                if not size_name:
                    continue
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attr.id})
                size_val_map[size_name] = size_val.id

        # Línea de atributos para la plantilla
        if color_val_map:
            attribute_lines.append((0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, list(color_val_map.values()))]
            }))
        if size_val_map:
            attribute_lines.append((0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, list(size_val_map.values()))]
            }))
        if attribute_lines:
            product_template.write({'attribute_line_ids': attribute_lines})
            _logger.info("Atributos y variantes asignadas correctamente.")

        # 8. Imagen por variante (color)
        for variant in product_template.product_variant_ids:
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
            if color_val:
                color_name = color_val.name
                color_obj = next((c for c in data.get("colors", []) if (c.get("colors", {}) or {}).get("es") == color_name or c.get("colorReference") == color_name), None)
                if color_obj:
                    img_url = color_obj.get("url_image")
                    if img_url:
                        variant_img_bin = get_image_binary_from_url(img_url)
                        if variant_img_bin:
                            variant.image_1920 = variant_img_bin
                            _logger.info(f"Imagen asignada a variante {variant.name}")

        # 9. LOG FINAL
        _logger.info("Producto NS300 y variantes creados correctamente con toda la info profesional B2B.")

        return product_template