import json
import logging
import requests
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
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            auth_response.raise_for_status()
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
            response.raise_for_status()
            data_list = response.json()
            data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
            _logger.info(f"📦 JSON recibido:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde API: {e}")
            return

        # Marca
        brand_data = data.get("brand") or {}
        brand_name = ""
        if isinstance(brand_data, dict):
            brand_name = brand_data.get("name", {}).get("es", "")
        if not brand_name:
            _logger.warning("⚠️ Marca no disponible.")

        # Datos básicos
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand_name} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = 9.8  # Valor ficticio por defecto
        standard_price = 0.0

        # Precio de coste
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                try:
                    price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                    standard_price = float(price_str)
                    break
                except Exception as e:
                    _logger.warning(f"⚠️ Error leyendo precio coste: {e}")
            if standard_price:
                break
        if not standard_price:
            _logger.warning("⚠️ No se pudo obtener precio de coste.")

        # Crear plantilla
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

        # Imagen principal
        img_url = ""
        for img in data.get("images", []):
            img_url = img.get("url_image", "")
            if img_url.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    img_response = requests.get(img_url)
                    content_type = img_response.headers.get("Content-Type", "")
                    if img_response.ok and "image" in content_type:
                        product_template.image_1920 = img_response.content
                        _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                        break
                    else:
                        _logger.warning(f"⚠️ Imagen no válida: {img_url} (Content-Type: {content_type})")
                except Exception as e:
                    _logger.warning(f"⚠️ Error cargando imagen principal desde {img_url}: {e}")

        # Imagen por variante
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name == "Color"
            ).name
            color_data = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color_value), None)
            variant_img = color_data.get("url_image") if color_data else None
            if variant_img:
                try:
                    variant_response = requests.get(variant_img)
                    if variant_response.ok and "image" in variant_response.headers.get("Content-Type", ""):
                        variant.image_1920 = variant_response.content
                        _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")
                    else:
                        _logger.warning(f"⚠️ Imagen no válida para variante {variant.name}")
                except Exception as e:
                    _logger.warning(f"⚠️ Error asignando imagen a variante {variant.name}: {e}")