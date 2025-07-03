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

        # --- Autenticación ---
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

        # --- DESCARGA TODO EL CATALOGO ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error al obtener catálogo: {response.status_code} - {response.text}")
        data = response.json()
        json_link = data.get("link")
        if not json_link:
            raise UserError("❌ No se recibió el link al JSON de catálogo completo.")

        catalog_resp = requests.get(json_link)
        if catalog_resp.status_code != 200:
            raise UserError(f"❌ Error descargando JSON catálogo: {catalog_resp.status_code} - {catalog_resp.text}")

        catalog = catalog_resp.json()
        # Si el JSON es lista, OK. Si tiene key "items", usar esa
        productos = catalog.get("items") if isinstance(catalog, dict) and "items" in catalog else catalog
        _logger.info(f"🔢 Total productos a procesar: {len(productos)}")

        for data in productos:
            # --- MARCA ---
            brand_data = data.get("brand") or {}
            brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
            if not brand:
                brand = "Sin Marca"

            # --- PLANTILLA PRINCIPAL ---
            name = data.get("designation", {}).get("es", "Producto sin nombre")
            full_name = f"{brand} {name}".strip()
            description = data.get("description", {}).get("es", "")
            default_code = data.get("catalogReference", "")

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

            template_vals = {
                'name': full_name,
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            product_template = self.create(template_vals)

            # --- Imagen principal SOLO UNA vez (la primera que encuentre) ---
            images = data.get("images", [])
            for img in images:
                img_url = img.get("url_image", "")
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        product_template.image_1920 = image_bin
                        break

            # --- INVENTARIO: obtiene SKUs reales de variantes ---
            # Si quieres aquí mismo puedes añadir las llamadas de inventario y precios por producto

            _logger.info(f"✅ Producto creado: {full_name} ({default_code})")

        _logger.info("✅✅✅ FIN DEL PROCESO. Todos los productos cargados.")

    # --- SERVER ACTION STOCK ---
    def sync_stock_from_api(self):
        # (Igual que ya tienes, sólo cambia la llamada para TODO el catálogo si quieres)
        pass

    # --- SERVER ACTION IMAGENES POR VARIANTE ---
    def sync_variant_images_from_api(self):
        # (Igual que ya tienes, sólo cambia la llamada para TODO el catálogo si quieres)
        pass