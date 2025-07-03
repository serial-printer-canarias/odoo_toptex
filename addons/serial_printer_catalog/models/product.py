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

        # 1. Autenticación
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

        # 2. Obtener el link del JSON del catálogo completo
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        catalog_response = requests.get(catalog_url, headers=headers)
        if catalog_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo catálogo: {catalog_response.status_code} - {catalog_response.text}")

        file_link = catalog_response.json().get("link")
        if not file_link:
            raise UserError("❌ No se obtuvo el link del JSON de productos Toptex.")
        _logger.info(f"📝 Link de catálogo recibido: {file_link}")

        # 3. Descargar el JSON crudo
        json_response = requests.get(file_link, headers=headers)
        if json_response.status_code != 200:
            raise UserError(f"❌ Error descargando el JSON catálogo: {json_response.status_code} - {json_response.text}")

        # 4. Log de la respuesta cruda (primeros 10.000 chars)
        try:
            json_text_preview = json_response.text[:10000]
            _logger.warning(f"RESPUESTA CRUDA DEL JSON DE PRODUCTOS:\n{json_text_preview}")
        except Exception as e:
            _logger.error(f"❌ Error al imprimir JSON: {str(e)}")

        # 5. Parsear el JSON
        try:
            catalog_data = json_response.json()
            if isinstance(catalog_data, dict) and "items" in catalog_data:
                catalog = catalog_data["items"]
            elif isinstance(catalog_data, list):
                catalog = catalog_data
            else:
                catalog = [catalog_data]
            _logger.info(f"🔄 Procesando {len(catalog)} productos TopTex...")
        except Exception as e:
            _logger.error(f"❌ Error interpretando el JSON: {str(e)}")
            catalog = []

        if not catalog:
            raise UserError("❌ El catálogo descargado no es una lista de productos válida.")

        # 6. Mapeo y creación de productos/variantes
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        for prod in catalog:
            try:
                brand = prod.get("brand", {}).get("name", {}).get("es", "") if isinstance(prod.get("brand", {}), dict) else ""
                if not brand:
                    brand = "TopTex"
                name = prod.get("designation", {}).get("es", prod.get("productReference", "Sin nombre"))
                description = prod.get("description", {}).get("es", "")
                default_code = prod.get("productReference") or prod.get("catalogReference", "")
                color_names = set()
                size_names = set()
                if prod.get("colors"):
                    # Nuevo modelo TopTex
                    for color in prod.get("colors"):
                        col_name = color.get("colors", {}).get("es", "") if isinstance(color.get("colors"), dict) else color.get("colors", "")
                        if col_name: color_names.add(col_name)
                        for sz in color.get("sizes", []):
                            if "size" in sz: size_names.add(sz.get("size"))
                # Alternativa por variantes planas
                if not color_names and "colors" in prod and isinstance(prod.get("colors"), dict):
                    color_names.add(prod["colors"].get("es", "Sin color"))
                if not size_names and "size" in prod:
                    size_names.add(prod["size"])

                # Atributos
                color_vals = {}
                for c in color_names:
                    val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                    color_vals[c] = val

                size_vals = {}
                for s in size_names:
                    val = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                    if not val:
                        val = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
                    size_vals[s] = val

                attribute_lines = []
                if color_vals:
                    attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]})
                if size_vals:
                    attribute_lines.append({'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]})

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

                # Imagen principal del producto (primera que encuentre)
                img_url = None
                # Nuevo modelo (Toptex nuevo)
                if prod.get("images"):
                    for img in prod.get("images", []):
                        img_url = img.get("url_image", "")
                        if img_url: break
                # Alternativo: packshots
                if not img_url and "packshots" in prod:
                    img_url = prod.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        product_template.image_1920 = image_bin

                # SKU, stock, precio por variante
                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                    size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
                    color_name = color_val.name if color_val else ""
                    size_name = size_val.name if size_val else ""
                    sku = ""
                    stock = 0
                    coste = 0.0

                    # SKU y precios (modelo plano de Toptex)
                    if prod.get("sizes"):
                        for sz in prod.get("sizes", []):
                            if sz.get("size") == size_name:
                                sku = sz.get("sku", "")
                                coste = float(sz.get("publicUnitPrice", 0))
                                stock = int(sz.get("stock", 0))
                    # Alternativo: SKU/stock/price en variantes del JSON
                    if not sku and prod.get("sku"):
                        sku = prod.get("sku", "")
                    if not coste and prod.get("publicUnitPrice"):
                        try:
                            coste = float(str(prod.get("publicUnitPrice")).replace(",", "."))
                        except:
                            coste = 0.0
                    if not stock and prod.get("stock"):
                        stock = int(prod.get("stock", 0))

                    variant.default_code = sku
                    variant.standard_price = coste
                    variant.lst_price = coste * 1.25 if coste > 0 else 9.8

                    # Stock real
                    StockQuant = self.env['stock.quant']
                    quant = StockQuant.search([
                        ('product_id', '=', variant.id),
                        ('location_id.usage', '=', 'internal')
                    ], limit=1)
                    if quant:
                        quant.quantity = stock
                        quant.inventory_quantity = stock

                    # Imagen por variante (colores FACE)
                    if color_name and prod.get("colors"):
                        for color_obj in prod.get("colors"):
                            col = color_obj.get("colors", {}).get("es", "")
                            if col == color_name:
                                img_color = color_obj.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                                if img_color:
                                    image_bin = get_image_binary_from_url(img_color)
                                    if image_bin:
                                        variant.image_1920 = image_bin

                    _logger.info(f"💰 Variante: {variant.name} | Coste: {coste} | Stock: {stock} | SKU: {sku}")

                _logger.info(f"✅ Producto {default_code} creado correctamente.")
            except Exception as e:
                _logger.error(f"❌ Error mapeando producto: {e}")