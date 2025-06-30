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
        _logger.warning(f"Error al descargar/convertir imagen: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_all_products_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("Faltan credenciales Toptex.")

        # --- Autenticación ---
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("No se recibió token válido.")

        # --- Llamada para obtener el link al fichero catálogo ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error catálogo Toptex: {response.status_code} - {response.text}")

        catalog_link = response.json().get("link")
        if not catalog_link:
            raise UserError("No se recibió link a fichero catálogo.")

        # --- Descargar el fichero de productos (puede ser gigante) ---
        catalog_file_resp = requests.get(catalog_link)
        if catalog_file_resp.status_code != 200:
            raise UserError("No se pudo descargar fichero catálogo.")
        try:
            products_list = catalog_file_resp.json()
        except Exception as e:
            raise UserError(f"Error leyendo el fichero de catálogo: {str(e)}")

        # --- Atributos globales (Color y Talla) ---
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        for product_data in products_list:
            try:
                brand_data = product_data.get("brand") or {}
                brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
                if not brand:
                    brand = "Toptex"
                name = product_data.get("designation", {}).get("es", "Producto sin nombre")
                full_name = f"{brand} {name}".strip()
                description = product_data.get("description", {}).get("es", "")
                default_code = product_data.get("catalogReference", "")
                images = product_data.get("images", [])

                # --- VARIANTES ---
                colors = product_data.get("colors", [])
                all_sizes = set()
                all_colors = set()
                for color in colors:
                    color_name = color.get("colors", {}).get("es", "")
                    all_colors.add(color_name)
                    for size in color.get("sizes", []):
                        all_sizes.add(size.get("size"))

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
                product_template = self.env['product.template'].create(template_vals)

                # Imagen principal (la primera que encuentre)
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product_template.image_1920 = image_bin
                            break

                # Aquí podrías mapear precios/sku de variantes si tienes el endpoint y necesitas ampliar.
                _logger.info(f"✅ Producto '{full_name}' creado ({default_code})")
            except Exception as e:
                _logger.error(f"❌ Error con producto {product_data.get('catalogReference', '?')}: {str(e)}")