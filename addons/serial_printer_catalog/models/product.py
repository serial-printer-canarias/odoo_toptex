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
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
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
        _logger.warning(f"❌ Error procesando imagen {url}: {str(e)}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # 1. Obtener credenciales
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # 2. Autenticación (token)
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

        # 3. Cargar info principal de producto
        catalog_reference = "NS300"   # ← Aquí el ref, luego lo haces variable para otros
        # (1) Info principal
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"
        # (2) Precios y stocks por SKU (variante)
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_reference}"
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_reference}"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        # --- PRODUCT DATA ---
        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
            data_list = response.json()
            data = data_list[0] if isinstance(data_list, list) and data_list else data_list
            _logger.info(f"📦 JSON producto:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error obteniendo producto: {e}")
            return

        # --- PRECIOS VARIANTES ---
        price_dict = {}  # SKU → precio
        try:
            res = requests.get(price_url, headers=headers)
            if res.status_code == 200:
                for item in res.json().get("items", []):
                    sku = item.get("sku")
                    price = None
                    for price_obj in item.get("prices", []):
                        if price_obj.get("quantity") == 1:
                            price = float(price_obj.get("price", 0))
                    if sku and price is not None:
                        price_dict[sku] = price
            _logger.info(f"💶 Precios variantes obtenidos para {len(price_dict)} SKUs")
        except Exception as e:
            _logger.warning(f"❌ Error obteniendo precios variantes: {e}")

        # --- STOCK VARIANTES ---
        stock_dict = {}  # SKU → stock
        try:
            res = requests.get(stock_url, headers=headers)
            if res.status_code == 200:
                for item in res.json().get("items", []):
                    sku = item.get("sku")
                    stock = 0
                    for warehouse in item.get("warehouses", []):
                        stock += int(warehouse.get("stock", 0))
                    if sku:
                        stock_dict[sku] = stock
            _logger.info(f"📦 Stocks variantes obtenidos para {len(stock_dict)} SKUs")
        except Exception as e:
            _logger.warning(f"❌ Error obteniendo stocks variantes: {e}")

        # --- MARCA ---
        brand_data = data.get("brand", {})
        brand = ""
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", {}).get("es") or brand_data.get("name", {}).get("en") or ""
        # Si tienes campo de marca personalizado en tu modelo, aquí lo asignas

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", catalog_reference)
        # Imagen principal
        images = data.get("images", [])
        main_image_bin = None
        for img in images:
            img_url = img.get("url_image")
            if img_url:
                main_image_bin = get_image_binary_from_url(img_url)
                break

        # --- ATRIBUTOS ---
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or \
            self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or \
            self.env['product.attribute'].create({'name': 'Talla'})

        # --- VARIANTES ---
        colors = data.get("colors", [])
        variant_lines = []
        color_vals = []
        size_vals = []
        for color in colors:
            color_name = color.get("colors", {}).get("es") or color.get("colors", {}).get("en")
            if not color_name:
                continue
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1) or self.env['product.attribute.value'].create({
                'name': color_name, 'attribute_id': color_attr.id
            })
            color_vals.append(color_val.id)
            for size in color.get("sizes", []):
                size_name = size.get("size")
                if not size_name:
                    continue
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1) or self.env['product.attribute.value'].create({
                    'name': size_name, 'attribute_id': size_attr.id
                })
                if size_val.id not in size_vals:
                    size_vals.append(size_val.id)

        # --- CREA LA PLANTILLA ---
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': 0.0,
            'standard_price': 0.0,
            'image_1920': main_image_bin,
            'categ_id': self.env.ref("product.product_category_all").id,
            # Si tienes campo de marca personalizado, aquí lo añades:
            # 'x_studio_marca': brand,
        }
        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Asigna atributos (solo si hay variantes, Odoo >=14)
        attribute_lines = [
            (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_vals)]}),
            (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_vals)]}),
        ]
        product_template.write({'attribute_line_ids': attribute_lines})
        _logger.info("✅ Atributos y valores asignados correctamente.")

        # --- ACTUALIZA CADA VARIANTE ---
        for variant in product_template.product_variant_ids:
            # Busca color y talla en la variante
            color_val = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.id == color_attr.id)
            size_val = variant.product_template_attribute_value_ids.filtered(
                lambda v: v.attribute_id.id == size_attr.id)
            # Construye el SKU para buscar precios/stocks
            sku = f"{default_code}C_{color_val.name}_{size_val.name}".replace(" ", "").replace("/", "")
            # Busca SKU real del JSON (puedes mapearlo mejor si te dan el SKU exacto)
            variant_price = 0.0
            variant_stock = 0
            # Busca por color y talla en los dicts
            for item in price_dict.keys():
                if color_val.name in item and size_val.name in item:
                    variant_price = price_dict[item]
                    break
            for item in stock_dict.keys():
                if color_val.name in item and size_val.name in item:
                    variant_stock = stock_dict[item]
                    break
            variant.write({
                'list_price': variant_price,
                'standard_price': variant_price,  # O usa otro dict si tienes coste separado
                'qty_available': variant_stock
            })
            _logger.info(f"💶 Variante {variant.name}: Precio {variant_price}, Stock {variant_stock}")

            # Imagen por variante (si tienes URL en color)
            color_obj = next((c for c in colors if (c.get("colors", {}).get("es") == color_val.name)), None)
            if color_obj:
                img_url = color_obj.get("url_image")
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🖼️ Imagen asignada a variante: {variant.name}")

        _logger.info(f"🎉 Producto {name} creado con todas las variantes, precios, stocks, imágenes y marca.")