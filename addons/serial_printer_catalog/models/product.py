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
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
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

        # 1. Autenticación y token
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

        # 2. Descarga de datos del producto NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=NS300&usage_right=b2b_b2c"
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
            # La API puede devolver una lista, tomamos el primer producto relevante
            data_list = response.json()
            if isinstance(data_list, list) and data_list:
                data = data_list[0]
            elif isinstance(data_list, dict):
                data = data_list
            else:
                raise UserError("❌ Datos de producto no válidos desde TopTex")
            _logger.info(f"📦 JSON interpretado:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde API: {e}")
            return

        # 3. Parsing seguro y mapping de campos principales
        brand_data = data.get("brand") or {}
        brand = ""
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", {}).get("es", "")
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = 0.0
        standard_price = 0.0
        stock_qty = 0

        # 4. Sacar precio coste, precio venta y stock de la variante MÁS BARATA
        found_price = False
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                # Sacar precio coste
                try:
                    price_cost = float(size.get("wholesaleUnitPrice", "0").replace(",", "."))
                except Exception:
                    price_cost = 0.0
                if not standard_price or price_cost < standard_price:
                    standard_price = price_cost
                    found_price = True
                # Sacar precio venta (usar retailUnitPrice si existe, si no, usar wholesale)
                try:
                    price_sale = float(size.get("retailUnitPrice", size.get("wholesaleUnitPrice", "0")).replace(",", "."))
                except Exception:
                    price_sale = 0.0
                if not list_price or price_sale < list_price:
                    list_price = price_sale
                # Sacar stock
                try:
                    stock = int(size.get("stock", 0))
                except Exception:
                    stock = 0
                stock_qty += stock
        _logger.info(f"💰 Precio de coste obtenido: {standard_price}")
        _logger.info(f"💸 Precio de venta obtenido: {list_price}")
        _logger.info(f"📦 Stock total obtenido: {stock_qty}")

        # 5. Crear plantilla de producto
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

        # 6. Crear atributos y variantes (color y talla)
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
            color_name = color.get("colors", {}).get("es") or color.get("name", "")
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name, 'attribute_id': color_attr.id
                })
            color_values.append(color_val.id)
            for size in color.get("sizes", []):
                size_name = size.get("size")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name, 'attribute_id': size_attr.id
                    })
                if size_val.id not in size_values:
                    size_values.append(size_val.id)
        # Atributos final
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

        # 7. Imagen principal del producto (primera de images[])
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                    break

        # 8. Imagen por variante de color
        for variant in product_template.product_variant_ids:
            color_value = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.name == "Color"
            ).name
            color_data = next((c for c in data.get("colors", []) if (c.get("colors", {}).get("es") or c.get("name", "")) == color_value), None)
            variant_img = color_data.get("url_image") if color_data else None
            if variant_img:
                image_bin = get_image_binary_from_url(variant_img)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")

        # 9. Asignar stock al producto (solo ejemplo, deberías integrar con el almacén real en Odoo)
        try:
            product_template.qty_available = stock_qty
            _logger.info(f"📦 Stock aplicado a producto: {stock_qty}")
        except Exception as e:
            _logger.warning(f"⚠️ Error aplicando stock: {str(e)}")

        _logger.info("✅ Sincronización completa para NS300.")