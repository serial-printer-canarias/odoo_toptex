import json
import logging
import requests
import base64
from PIL import Image
from io import BytesIO
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"📥 Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(BytesIO(response.content))
            image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG")
            image_bytes = output.getvalue()
            _logger.info(f"🖼️ Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Contenido no válido como imagen: {url}")
            return None
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {e}")
        return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Parámetros desde el sistema
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("🚫 Faltan credenciales o parámetros del sistema.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")

        token = auth_response.json().get("token")
        if not token:
            raise UserError("🚫 Token no recibido correctamente.")
        _logger.info("🔐 Token recibido correctamente.")

        # Obtener producto por catalog_reference
        catalog_ref = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_references={catalog_ref}&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br",
        }

        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")

        data = response.json()
        data_list = data if isinstance(data, list) else data.get("items", [])
        if not data_list:
            _logger.error("❌ No se obtuvo ningún producto desde la API.")
            return

        data = data_list[0]  # Solo trabajamos con NS300
        _logger.info("📦 JSON interpretado:\n" + json.dumps(data, indent=2))

        # Marca y descripción
        description = data.get("description", {}).get("es", "Sin descripción")
        brand = data.get("brand", {}).get("name", {}).get("es", "Sin marca")
        translated_name = data.get("designation", {}).get("es", catalog_ref)
        full_name = f"{translated_name} - {brand}"

        # Precio de coste desde endpoint /price
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
        price_response = requests.get(price_url, headers=headers)
        standard_price = 0.0
        if price_response.status_code == 200:
            try:
                price_json = price_response.json()
                for entry in price_json:
                    for price_info in entry.get("prices", []):
                        if price_info.get("quantity") == 1:
                            standard_price = float(price_info.get("price", 0.0))
                            break
            except Exception as e:
                _logger.warning(f"⚠️ Error al procesar precio: {e}")

        # Stock desde endpoint /inventory
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        stock_response = requests.get(stock_url, headers=headers)
        stock_quantity = 0
        if stock_response.status_code == 200:
            try:
                stock_json = stock_response.json()
                for entry in stock_json:
                    if entry.get("id") == "toptex":
                        stock_quantity = entry.get("stock", 0)
                        break
            except Exception as e:
                _logger.warning(f"⚠️ Error al procesar stock: {e}")

        # Crear plantilla
        template_vals = {
            "name": full_name,
            "default_code": catalog_ref,
            "type": "consu",
            "description_sale": description,
            "list_price": standard_price * 2,
            "standard_price": standard_price,
            "categ_id": self.env.ref("product.product_category_all").id,
            "sale_ok": True,
            "purchase_ok": True,
        }
        _logger.info(f"🧩 Datos para crear plantilla: {template_vals}")
        template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {full_name}")

        # Atributos
        attribute_lines = []
        for color in data.get("colors", []):
            color_name = color.get("translatedColor", {}).get("es")
            color_attr = self.env["product.attribute"].search([("name", "=", "Color")], limit=1)
            color_val = self.env["product.attribute.value"].search([("name", "=", color_name), ("attribute_id", "=", color_attr.id)], limit=1)
            if not color_val:
                color_val = self.env["product.attribute.value"].create({"name": color_name, "attribute_id": color_attr.id})
            attribute_lines.append((0, 0, {"attribute_id": color_attr.id, "value_ids": [(6, 0, [color_val.id])]}))

        for size in data.get("sizes", []):
            size_name = size.get("translatedSize", {}).get("es")
            size_attr = self.env["product.attribute"].search([("name", "=", "Talla")], limit=1)
            size_val = self.env["product.attribute.value"].search([("name", "=", size_name), ("attribute_id", "=", size_attr.id)], limit=1)
            if not size_val:
                size_val = self.env["product.attribute.value"].create({"name": size_name, "attribute_id": size_attr.id})
            attribute_lines.append((0, 0, {"attribute_id": size_attr.id, "value_ids": [(6, 0, [size_val.id])]}))

        if attribute_lines:
            template.write({"attribute_line_ids": attribute_lines})
            _logger.info("✅ Atributos y variantes asignados correctamente.")

        # Imagen principal
        images = data.get("images", [])
        if images:
            main_url = images[0].get("url")
            image_bin = get_image_binary_from_url(main_url)
            if image_bin:
                template.image_1920 = image_bin
                _logger.info(f"🖼️ Imagen principal asignada desde {main_url}")

        # Imagen por variante
        for variant in template.product_variant_ids:
            variant_color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == "Color")
            color_data = next((c for c in data.get("colors", []) if c.get("translatedColor", {}).get("es") == variant_color.name), None)
            if color_data:
                img_url = color_data.get("images", [{}])[0].get("url")
                if img_url:
                    variant.image_1920 = get_image_binary_from_url(img_url)
                    _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")