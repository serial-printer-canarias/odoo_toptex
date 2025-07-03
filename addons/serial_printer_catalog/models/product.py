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
        response = requests.get(url, stream=True, timeout=15)
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
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen {url}: {str(e)}")
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

        # 1. AUTENTICACIÓN
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

        # 2. LLAMADA AL CATÁLOGO GENERAL
        product_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        resp = requests.get(product_url, headers=headers)
        if resp.status_code != 200:
            raise UserError(f"❌ Error al obtener catálogo: {resp.status_code} - {resp.text}")

        link = resp.json().get("link")
        if not link:
            raise UserError("❌ No se recibió el enlace para descargar el JSON completo.")

        _logger.info(f"🔗 Enlace JSON: {link}")

        # 3. DESCARGAR EL ARCHIVO JSON
        file_resp = requests.get(link)
        if file_resp.status_code != 200:
            raise UserError(f"❌ Error al descargar el archivo JSON: {file_resp.status_code} - {file_resp.text}")

        try:
            data = file_resp.json()
        except Exception as e:
            raise UserError(f"❌ Error parseando JSON: {str(e)}")

        _logger.warning(f"🌐 RESPUESTA CRUDA DEL CATALOGO: {json.dumps(data)[:3000]}...")  # log primeros 3000 chars

        # 4. RECORRER TODOS LOS PRODUCTOS
        productos = data if isinstance(data, list) else data.get("products", [])
        if not productos:
            _logger.error("❌ El catálogo descargado no es una lista de productos.")
            return

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        for producto in productos:
            try:
                name = producto.get("designation", {}).get("es", "Sin nombre")
                brand = producto.get("brand", {}).get("name", {}).get("es", "Sin marca")
                description = producto.get("description", {}).get("es", "")
                default_code = producto.get("catalogReference") or producto.get("productReference") or ""

                # VARIANTES Y ATRIBUTOS
                colors_data = producto.get("colors", [])
                all_colors = set()
                all_sizes = set()
                for color in colors_data:
                    color_name = color.get("colors", {}).get("es", "")
                    all_colors.add(color_name)
                    for size in color.get("sizes", []):
                        all_sizes.add(size.get("size"))

                color_vals = {}
                for c in all_colors:
                    if not c: continue
                    val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                    color_vals[c] = val

                size_vals = {}
                for s in all_sizes:
                    if not s: continue
                    val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                    size_vals[s] = val

                attribute_lines = []
                if color_vals:
                    attribute_lines.append({
                        'attribute_id': color_attr.id,
                        'value_ids': [(6, 0, [v.id for v in color_vals.values()])]
                    })
                if size_vals:
                    attribute_lines.append({
                        'attribute_id': size_attr.id,
                        'value_ids': [(6, 0, [v.id for v in size_vals.values()])]
                    })

                template_vals = {
                    'name': f"{brand} {name}".strip(),
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                }
                product_template = self.create(template_vals)

                # IMAGEN PRINCIPAL
                images = producto.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product_template.image_1920 = image_bin
                            break

                # INVENTARIO y PRECIOS por variante
                inventory_items = producto.get("inventory", [])
                price_items = producto.get("prices", [])
                def get_sku(color, size):
                    for item in inventory_items:
                        if item.get("color") == color and item.get("size") == size:
                            return item.get("sku")
                    return ""

                def get_price_cost(color, size):
                    for item in price_items:
                        if item.get("color") == color and item.get("size") == size:
                            prices = item.get("prices", [])
                            if prices:
                                return float(prices[0].get("price", 0.0))
                    return 0.0

                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""
                    sku = get_sku(color_name, size_name)
                    if sku:
                        variant.default_code = sku
                    coste = get_price_cost(color_name, size_name)
                    variant.standard_price = coste
                    variant.lst_price = coste * 1.25 if coste > 0 else 9.8
                    _logger.info(f"💰 Variante: {variant.name} | Coste: {coste}")

                _logger.info(f"✅ Producto creado: {brand} {name} ({default_code})")
            except Exception as e:
                _logger.error(f"❌ Error al crear producto: {str(e)} | {producto}")

        _logger.info("🎉 FIN: Todos los productos del catálogo procesados.")