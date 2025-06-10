import json
import logging
import requests
import base64
from PIL import Image
from io import BytesIO
from odoo import models, api

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(BytesIO(response.content))
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format="JPEG")
            image_bytes = img_byte_arr.getvalue()
            _logger.info(f"🟢 Imagen convertida a binario ({len(image_bytes)} bytes)")
            return base64.b64encode(image_bytes)
        else:
            raise ValueError("Contenido no válido como imagen")
    except Exception as e:
        _logger.warning(f"⚠️ Error al procesar imagen desde {url}: {e}")
        return None

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def sync_product_from_api(self):
        try:
            # Parámetros del sistema
            username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
            password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
            api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
            proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')

            if not username or not password or not api_key or not proxy_url:
                raise ValueError("Faltan credenciales o URL del proxy en parámetros del sistema")

            # Obtener token
            auth_url = f"{proxy_url}/v3/authenticate"
            auth_payload = {"username": username, "password": password}
            auth_headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
            if auth_response.status_code != 200:
                raise ValueError(f"Error autenticando: {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise ValueError("Token vacío")

            # Llamada principal del producto por catalog_reference
            product_url = f"{proxy_url}/v3/products?catalog_references=NS300&usage_right=b2b_b2c"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token,
                "Accept-Encoding": "gzip, deflate, br"
            }
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise ValueError(f"Error al obtener producto: {response.text}")

            data = response.json()
            if isinstance(data, list):
                data = data[0] if data else {}
            if not data:
                raise ValueError("No se recibió data válida del producto")

            # Obtener stock
            inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference=NS300"
            inventory_resp = requests.get(inventory_url, headers=headers)
            stock_qty = 0
            if inventory_resp.status_code == 200:
                stock_data = inventory_resp.json()
                stock_qty = stock_data[0].get("stock", 0) if stock_data else 0

            # Obtener precio
            price_url = f"{proxy_url}/v3/products/price?catalog_reference=NS300"
            price_resp = requests.get(price_url, headers=headers)
            cost_price = 0.0
            if price_resp.status_code == 200:
                price_data = price_resp.json()
                for p in price_data.get("prices", []):
                    if p.get("quantity") == 1:
                        cost_price = float(p.get("price", "0").replace(",", "."))

            name = data.get("translatedName", {}).get("es", "Producto sin nombre")
            description = data.get("description", {}).get("es", "")
            default_code = data.get("catalogReference", "NS300")
            brand = data.get("brand", {}).get("name", {}).get("es", "Sin marca")

            template_vals = {
                "name": f"{name} - {brand}",
                "default_code": default_code,
                "type": "consu",
                "detailed_type": "consu",
                "description_sale": description,
                "standard_price": cost_price,
                "list_price": cost_price * 2,
                "image_1920": False,
                "categ_id": self.env.ref("product.product_category_all").id,
            }

            _logger.info(f"📦 Datos para crear plantilla: {template_vals}")
            product_template = self.create(template_vals)
            _logger.info(f"✅ Plantilla creada: {product_template.name}")

            # Atributos
            attribute_lines = []
            for color in data.get("colors", []):
                color_name = color.get("color", {}).get("name", {}).get("es")
                if not color_name:
                    continue
                color_attr = self.env["product.attribute"].search([("name", "=", "Color")], limit=1)
                if not color_attr:
                    color_attr = self.env["product.attribute"].create({"name": "Color"})
                color_val = self.env["product.attribute.value"].search([
                    ("name", "=", color_name), ("attribute_id", "=", color_attr.id)
                ], limit=1)
                if not color_val:
                    color_val = self.env["product.attribute.value"].create({
                        "name": color_name,
                        "attribute_id": color_attr.id
                    })
                attribute_lines.append((0, 0, {
                    "attribute_id": color_attr.id,
                    "value_ids": [(6, 0, [color_val.id])]
                }))

            for size in data.get("sizes", []):
                size_name = size.get("size", {}).get("name", {}).get("es")
                if not size_name:
                    continue
                size_attr = self.env["product.attribute"].search([("name", "=", "Talla")], limit=1)
                if not size_attr:
                    size_attr = self.env["product.attribute"].create({"name": "Talla"})
                size_val = self.env["product.attribute.value"].search([
                    ("name", "=", size_name), ("attribute_id", "=", size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env["product.attribute.value"].create({
                        "name": size_name,
                        "attribute_id": size_attr.id
                    })
                attribute_lines.append((0, 0, {
                    "attribute_id": size_attr.id,
                    "value_ids": [(6, 0, [size_val.id])]
                }))

            if attribute_lines:
                product_template.attribute_line_ids = attribute_lines
                _logger.info("✅ Atributos asignados correctamente.")

            # Imagen principal
            images = data.get("images", [])
            if images:
                image_url = images[0].get("url")
                if image_url:
                    image_bin = get_image_binary_from_url(image_url)
                    if image_bin:
                        product_template.image_1920 = image_bin
                        _logger.info(f"🖼️ Imagen principal asignada desde {image_url}")

            # Imagen por color
            for variant in product_template.product_variant_ids:
                color_name = variant.attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name == "Color"
                ).name
                color_data = next((c for c in data.get("colors", []) if c.get("color", {}).get("name", {}).get("es") == color_name), None)
                if color_data:
                    variant_images = color_data.get("images", [])
                    if variant_images:
                        variant_url = variant_images[0].get("url")
                        variant_bin = get_image_binary_from_url(variant_url)
                        if variant_bin:
                            variant.image_1920 = variant_bin
                            _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")

            # Stock
            for variant in product_template.product_variant_ids:
                variant.qty_available = stock_qty

        except Exception as e:
            _logger.error(f"❌ Error en sincronización: {e}")