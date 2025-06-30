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
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # PETICIÓN CATÁLOGO COMPLETO
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener el catálogo: {response.status_code} - {response.text}")
        data = response.json()
        if "link" not in data:
            raise UserError("❌ No se recibió el link al catálogo completo.")
        catalog_file_url = data["link"]

        # DESCARGA EL ARCHIVO DEL CATÁLOGO COMPLETO
        file_resp = requests.get(catalog_file_url)
        if file_resp.status_code != 200:
            raise UserError(f"❌ No se pudo descargar el catálogo: {file_resp.status_code}")
        catalog_json = file_resp.json()
        if not isinstance(catalog_json, list):
            raise UserError("❌ El catálogo descargado no tiene formato lista.")

        for data in catalog_json:
            try:
                # --- MARCA ---
                brand_data = data.get("brand") or {}
                brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
                if not brand:
                    brand = "Native Spirit"

                # --- PLANTILLA PRINCIPAL ---
                name = data.get("designation", {}).get("es", "Producto sin nombre")
                full_name = f"{brand} {name}".strip()
                description = data.get("description", {}).get("es", "")
                default_code = data.get("catalogReference", "SN")

                # --- VARIANTES ---
                colors = data.get("colors", [])
                all_sizes = set()
                all_colors = set()
                for color in colors:
                    color_name = color.get("colors", {}).get("es", "")
                    all_colors.add(color_name)
                    for size in color.get("sizes", []):
                        all_sizes.add(size.get("size"))

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

                template = self.search([('default_code', '=', default_code)], limit=1)
                if not template:
                    template_vals = {
                        'name': full_name,
                        'default_code': default_code,
                        'type': 'consu',
                        'is_storable': True,
                        'description_sale': description,
                        'categ_id': self.env.ref("product.product_category_all").id,
                        'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    }
                    template = self.create(template_vals)
                else:
                    template.write({
                        'name': full_name,
                        'description_sale': description,
                        'attribute_line_ids': [(0, 0, line) for line in attribute_lines]
                    })

                images = data.get("images", [])
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            template.image_1920 = image_bin
                            break

                _logger.info(f"✅ Producto {default_code} ({full_name}) sincronizado.")

            except Exception as e:
                _logger.error(f"❌ Error sincronizando producto: {str(e)}")

        _logger.info("🚀 Sincronización de Catálogo Toptex completada.")

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        inventory_url = f"{proxy_url}/v3/products/inventory/all"
        headers.update({"x-toptex-authorization": token})
        inv_resp = requests.get(inventory_url, headers=headers)
        if inv_resp.status_code != 200:
            _logger.error("❌ Error al obtener inventario: " + inv_resp.text)
            return

        inventory_items = inv_resp.json().get("items", [])

        StockQuant = self.env['stock.quant']
        for item in inventory_items:
            sku = item.get("sku")
            stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
            template = self.env['product.template'].search([('default_code', '=', item.get("catalogReference", ""))], limit=1)
            if not template:
                continue
            product = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
            if product:
                quant = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                if quant:
                    quant.quantity = stock
                    quant.inventory_quantity = stock
                    _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    StockQuant.create({
                        'product_id': product.id,
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'quantity': stock,
                        'inventory_quantity': stock,
                    })
                    _logger.info(f"➕ Stock.quant creado para {sku} con stock {stock}")
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json={"username": username, "password": password}, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return

        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            _logger.error(f"❌ Error al obtener catálogo para imágenes: {response.text}")
            return
        data = response.json()
        if "link" not in data:
            _logger.error("❌ No se recibió el link al catálogo completo para imágenes.")
            return
        catalog_file_url = data["link"]

        file_resp = requests.get(catalog_file_url)
        if file_resp.status_code != 200:
            _logger.error(f"❌ No se pudo descargar el catálogo para imágenes: {file_resp.status_code}")
            return
        catalog_json = file_resp.json()

        for data in catalog_json:
            default_code = data.get("catalogReference", "")
            template = self.search([('default_code', '=', default_code)], limit=1)
            if not template:
                continue

            colors = data.get("colors", [])
            color_images = {
                color.get("colors", {}).get("es", ""): color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for color in colors
            }

            for variant in template.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                color_name = color_val.name if color_val else ""
                img_url = color_images.get(color_name)
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🖼️ Imagen FACE asignada a {variant.default_code}")

# FIN