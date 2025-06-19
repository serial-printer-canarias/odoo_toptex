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
        content_type = response.headers.get("Content-Type", "")
        if response.status_code == 200 and "image" in content_type:
            image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
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

        # Autenticación
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

        # Llamadas a API de productos, precios y stocks por SKU (optimizado para NS300)
        catalog_ref = "ns300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        # Descarga datos de producto base (primera variante)
        product_response = requests.get(product_url, headers=headers)
        data = product_response.json()[0] if isinstance(product_response.json(), list) else product_response.json()
        _logger.info(f"📦 JSON interpretado:\n{json.dumps(data, indent=2)}")

        # Descarga precios y stock para TODAS las variantes (por SKU)
        inventory_response = requests.get(inventory_url, headers=headers)
        price_response = requests.get(price_url, headers=headers)
        inventory_json = inventory_response.json()
        price_json = price_response.json()

        # Mapear por SKU rápido:
        inventory_map = {}
        for item in inventory_json.get("items", []):
            inventory_map[item.get("sku", "")] = item.get("warehouses", [{}])[0].get("stock", 0)

        price_map = {}
        for item in price_json.get("items", []):
            sku = item.get("sku", "")
            price = 0.0
            if item.get("prices"):
                price = float(item["prices"][0]["price"])
            price_map[sku] = price

        # Marca (Many2one) si existe el modelo (quitar el bloque si no tienes el modelo product.brand)
        brand_name = data.get("brand", {}).get("name", {}).get("es", "")
        brand_id = None
        if brand_name:
            ProductBrand = self.env['product.brand']
            brand = ProductBrand.search([('name', '=', brand_name)], limit=1)
            if not brand:
                brand = ProductBrand.create({'name': brand_name})
            brand_id = brand.id

        # Datos generales plantilla
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        categ_id = self.env.ref("product.product_category_all").id

        # Imagen principal
        image_1920 = None
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_1920 = get_image_binary_from_url(img_url)
                break

        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',  # Consu porque "product" no funciona para tu flujo
            'description_sale': description,
            'image_1920': image_1920,
            'categ_id': categ_id,
        }
        if brand_id:
            template_vals['brand_id'] = brand_id

        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # Atributos
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1) or self.env['product.attribute.value'].create({
                'name': color_name, 'attribute_id': color_attr.id
            })
            color_values.append(color_val.id)
            for size in color.get("sizes", []):
                size_name = size.get("size")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1) or self.env['product.attribute.value'].create({
                    'name': size_name, 'attribute_id': size_attr.id
                })
                if size_val.id not in size_values:
                    size_values.append(size_val.id)

        attribute_lines.append({
            'attribute_id': color_attr.id,
            'value_ids': [(6, 0, color_values)],
        })
        attribute_lines.append({
            'attribute_id': size_attr.id,
            'value_ids': [(6, 0, size_values)],
        })

        if attribute_lines:
            product_template.write({
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines]
            })
            _logger.info("✅ Atributos y valores asignados correctamente.")

        # Ahora toca variantes, precios, stocks e imágenes individuales por variante:
        for variant in product_template.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == "Color").name
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == "Talla").name
            sku = f"{default_code}C_{data['colors'][[c.get('colors', {}).get('es') for c in data['colors']].index(color)]['colorCode']}_{[s.get('size') for s in data['colors'][[c.get('colors', {}).get('es') for c in data['colors']].index(color)]['sizes']].index(size)+68495}"  # Genera el SKU exacto como en tu Postman si hace falta

            # Precio, coste y stock
            list_price = price_map.get(sku, 0.0)
            standard_price = list_price  # Puedes ajustar si necesitas otro endpoint para coste
            stock = inventory_map.get(sku, 0)

            variant.list_price = list_price
            variant.standard_price = standard_price
            variant.qty_available = stock

            # Imagen por variante (si la tienes por color)
            color_obj = next((c for c in data.get("colors", []) if c.get("colors", {}).get("es") == color), None)
            variant_img_url = color_obj.get("url_image") if color_obj else None
            if variant_img_url:
                variant.image_1920 = get_image_binary_from_url(variant_img_url)

            _logger.info(f"Variante {variant.name} coste {standard_price} stock {stock} foto {'OK' if variant_img_url else 'NO'}")

        _logger.info("🎉 Producto NS300 creado y listo para ventas B2B/B2C en Odoo!")