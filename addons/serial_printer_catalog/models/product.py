import urllib.request
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
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
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

def descargar_json(url):
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                json_data = json.loads(data)
                _logger.info("✅ JSON de catálogo descargado correctamente")
                return json_data
            else:
                _logger.error(f"❌ Error al descargar JSON. Código: {response.status}")
    except Exception as e:
        _logger.error(f"❌ Excepción al descargar JSON: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_catalog_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # --- 1. Autenticación ---
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

        # --- 2. Obtener link temporal del catálogo completo ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        catalog_response = requests.get(catalog_url, headers=headers)
        if catalog_response.status_code != 200:
            raise UserError(f"❌ Error al obtener link de catálogo: {catalog_response.status_code} - {catalog_response.text}")

        catalog_json = catalog_response.json()
        link_json = catalog_json.get("link") or catalog_json.get("url") or None
        if not link_json:
            raise UserError("❌ No se recibió enlace de catálogo all.")
        _logger.info(f"🔗 Link temporal catálogo all: {link_json}")

        # --- 3. Descargar catálogo desde el link temporal ---
        catalogo_all = descargar_json(link_json)
        if not catalogo_all:
            raise UserError("❌ No se pudo descargar el JSON de catálogo all.")
        _logger.info(f"📦 Catálogo descargado: {len(catalogo_all)} productos encontrados.")

        # --- 4. Procesar productos (creación/actualización en Odoo) ---
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})
        created_count = 0
        for producto in catalogo_all:
            try:
                brand = producto.get("brand", {}).get("name", {}).get("es", "") or "TopTex"
                name = producto.get("designation", {}).get("es", producto.get("productReference", "Producto sin nombre"))
                description = producto.get("description", {}).get("es", "")
                default_code = producto.get("catalogReference") or producto.get("productReference") or ""
                colors_data = producto.get("colors", [])
                all_colors = set()
                all_sizes = set()

                # Analiza variantes de color y talla
                for color in colors_data:
                    color_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                    all_colors.add(color_name)
                    for sz in color.get("sizes", []):
                        all_sizes.add(sz.get("size"))

                # Atributos/valores en Odoo
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

                # Plantilla principal Odoo
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

                # Imagen principal (la primera válida de cualquier variante)
                images = producto.get("images", [])
                img_asignada = False
                for img in images:
                    url_img = img.get("url_image")
                    if url_img:
                        image_bin = get_image_binary_from_url(url_img)
                        if image_bin:
                            template.image_1920 = image_bin
                            img_asignada = True
                            break

                # Variantes, SKUs, precio, imágenes por variante
                for variant in template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""
                    sku = ""
                    price = 0.0
                    # Busca info de variantes para SKU/precio/imágenes
                    for color in colors_data:
                        color_es = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                        if color_es == color_name:
                            for sz in color.get("sizes", []):
                                if sz.get("size") == size_name:
                                    sku = sz.get("sku", "")
                                    # Precio
                                    prices = sz.get("prices", [])
                                    if prices:
                                        price = float(prices[0].get("price", 0.0))
                                    # Imagen por variante (FACE principal)
                                    packshots = color.get("packshots", {})
                                    face = packshots.get("FACE", {})
                                    url_face = face.get("url_packshot")
                                    if url_face:
                                        variant.image_1920 = get_image_binary_from_url(url_face)
                    if sku:
                        variant.default_code = sku
                    if price:
                        variant.standard_price = price
                        variant.lst_price = price * 1.25

                created_count += 1
                _logger.info(f"✅ Producto {name} ({default_code}) creado correctamente con variantes.")
            except Exception as e:
                _logger.error(f"❌ Error procesando producto: {e}")

        _logger.info(f"🎉 Catálogo completo cargado: {created_count} productos procesados.")