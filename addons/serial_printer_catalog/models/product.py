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
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(response.content))
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
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

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Petición para obtener el enlace temporal de productos
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Descargar el JSON de productos usando los mismos headers (por si requiere token)
        file_response = requests.get(file_url, headers=headers)
        if file_response.status_code != 200:
            raise UserError(f"❌ Error descargando JSON de productos: {file_response.status_code} - {file_response.text}")
        try:
            products_data = file_response.json()
        except Exception as e:
            raise UserError(f"❌ No se pudo decodificar el JSON: {str(e)}")

        _logger.info(f"💾 RESPUESTA CRUDA DEL JSON DE PRODUCTOS: {products_data}")

        if not isinstance(products_data, list) or not products_data:
            _logger.warning("🚨 El catálogo descargado no es una lista de productos válida.")
            return

        _logger.info(f"🟢 Procesando {len(products_data)} productos TopTex...")

        # 4. Procesar y mapear cada producto
        for prod in products_data:
            brand = prod.get("brand", {}).get("name", {}).get("es", "") or "TopTex"
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            colors = prod.get("colors", [])
            images = prod.get("images", [])
            prices = prod.get("prices", [])
            variants = prod.get("sizes", [])

            # Atributos de color/talla
            all_colors = set()
            all_sizes = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "")
                all_colors.add(color_name)
                for size in color.get("sizes", []):
                    all_sizes.add(size.get("size"))

            # Crear atributos si no existen
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

            attribute_lines = []
            if all_colors:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                })
            if all_sizes:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                })

            # Crear producto
            template_vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            template = self.create(template_vals)

            # Imagen principal (la primera que encuentre)
            if images:
                img_url = images[0].get("url_image")
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        template.image_1920 = image_bin

            # Mapear variantes: SKU, precio, stock e imagen individual
            for variant in template.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                color_name = color_val.name if color_val else ""
                size_name = size_val.name if size_val else ""
                # Buscar datos para esta variante
                for c in colors:
                    col_name = c.get("colors", {}).get("es", "")
                    if col_name == color_name:
                        for sz in c.get("sizes", []):
                            if sz.get("size") == size_name:
                                # SKU
                                variant.default_code = sz.get("sku", "")
                                # Precio
                                prices = sz.get("prices", [])
                                if prices:
                                    variant.standard_price = float(prices[0].get("price", 0.0))
                                    variant.lst_price = float(prices[0].get("price", 0.0)) * 1.25
                                # Stock (ejemplo)
                                stock = sz.get("stock", 0)
                                quant = self.env['stock.quant'].search([
                                    ('product_id', '=', variant.id),
                                    ('location_id.usage', '=', 'internal')
                                ], limit=1)
                                if quant:
                                    quant.quantity = stock
                                    quant.inventory_quantity = stock
                                # Imagen por variante (si existe)
                                img_url = c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                                if img_url:
                                    image_bin = get_image_binary_from_url(img_url)
                                    if image_bin:
                                        variant.image_1920 = image_bin

        _logger.info("✅ Sincronización completa de productos TopTex.")