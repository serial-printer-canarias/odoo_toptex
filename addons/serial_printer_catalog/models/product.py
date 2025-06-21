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
    def sync_toptex_product_ns300(self):
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
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # Descarga info NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)
        _logger.info(f"📥 Respuesta cruda:\n{response.text}")
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
        data_list = response.json()
        data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
        _logger.info(f"📦 JSON interpretado:\n{json.dumps(data, indent=2)}")

        # --- MARCA ---
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        # --- PLANTILLA PRINCIPAL ---
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip() if brand else name
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # --- VARIANTES ---
        colors = data.get("colors", [])
        all_sizes = set()
        all_colors = set()
        for color in colors:
            color_name = color.get("colors", {}).get("es", "")
            if color_name:
                all_colors.add(color_name)
            for size in color.get("sizes", []):
                sz = size.get("size")
                if sz:
                    all_sizes.add(sz)

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        color_vals = {}
        for c in all_colors:
            val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
            color_vals[c] = val

        size_vals = {}
        for s in all_sizes:
            val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
            size_vals[s] = val

        attribute_lines = [
            {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
            },
            {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
            }
        ]

        # --- PLANTILLA ---
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',  # MUY IMPORTANTE: si pones 'product' rompe
            'description_sale': description,
            'categ_id': self.env.ref("product.product_category_all").id,
            'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
        }
        _logger.info(f"🛠️ Datos para crear plantilla: {template_vals}")
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # --- IMAGEN PRINCIPAL ---
        images = data.get("images", [])
        for img in images:
            img_url = img.get("url_image", "")
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    product_template.image_1920 = image_bin
                    _logger.info(f"🖼️ Imagen principal asignada desde: {img_url}")
                    break

        # --- PRECIO DE COSTE Y VENTA POR VARIANTE ---
        # Saca un precio coste por defecto (ejemplo el primero que encuentre, puedes mejorar la lógica)
        price_cost = 0.0
        for color in colors:
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    price_cost = float(price_str)
                    break
                except Exception:
                    continue
            if price_cost:
                break

        for variant in product_template.product_variant_ids:
            variant.standard_price = price_cost
            variant.lst_price = price_cost * 1.25 if price_cost > 0 else 9.8

    @api.model
    def update_toptex_stock_ns300(self):
        """Actualiza el stock de cada variante NS300 desde TopTex"""
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # AUTENTICACIÓN
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        if not token:
            _logger.error("Sin token de Toptex, abortando actualización de stock.")
            return

        # LLAMADA STOCK
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference=ns300"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        resp = requests.get(stock_url, headers=headers)
        if resp.status_code != 200:
            _logger.error(f"Error al obtener stock: {resp.status_code} - {resp.text}")
            return

        stock_data = resp.json()
        items = stock_data.get("items", []) if isinstance(stock_data, dict) else stock_data
        for item in items:
            color = item.get("color")
            size = item.get("size")
            available = item.get("stock", 0)
            # Buscar variante en Odoo por atributos
            domain = [
                ('product_tmpl_id.default_code', '=', 'NS300'),
                ('attribute_value_ids.name', '=', color),
                ('attribute_value_ids.name', '=', size)
            ]
            variant = self.env['product.product'].search(domain, limit=1)
            if variant:
                variant.qty_available = available
                _logger.info(f"Stock actualizado: {variant.name} => {available}")

    @api.model
    def update_toptex_variant_images_ns300(self):
        """Actualiza la imagen de cada variante NS300 según color"""
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # AUTENTICACIÓN
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        token = auth_response.json().get("token")
        if not token:
            _logger.error("Sin token de Toptex, abortando actualización de imágenes.")
            return

        # LLAMADA PRODUCTO
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        resp = requests.get(product_url, headers=headers)
        if resp.status_code != 200:
            _logger.error(f"Error al obtener producto: {resp.status_code} - {resp.text}")
            return

        data_list = resp.json()
        data = data_list[0] if isinstance(data_list, list) and data_list else data_list
        color_data = {c.get("colors", {}).get("es"): c for c in data.get("colors", [])}

        # Buscar variantes y actualizar imagen según color
        variants = self.env['product.product'].search([('product_tmpl_id.default_code', '=', 'NS300')])
        for variant in variants:
            color_name = ""
            for v in variant.product_template_attribute_value_ids:
                if v.attribute_id.name == "Color":
                    color_name = v.name
            color_info = color_data.get(color_name)
            img_url = color_info.get("url_image") if color_info else ""
            if img_url:
                image_bin = get_image_binary_from_url(img_url)
                if image_bin:
                    variant.image_1920 = image_bin
                    _logger.info(f"Imagen de variante {variant.name} actualizada con {img_url}")