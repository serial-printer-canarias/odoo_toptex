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

        # --- Obtención del link temporal del catálogo entero ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        resp = requests.get(catalog_url, headers=headers)
        if resp.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {resp.status_code} - {resp.text}")
        catalog_json = resp.json()
        link_url = catalog_json.get("link") or next(iter(catalog_json.values()), "")
        if not link_url:
            raise UserError("❌ No se recibió enlace de descarga del catálogo.")
        _logger.info(f"📥 Enlace JSON: {link_url}")

        # --- Descarga del JSON del catálogo ---
        data_response = requests.get(link_url)
        try:
            data = data_response.json()
            _logger.info(f"🟢 Inicio del JSON recibido: {json.dumps(data)[:2000]}")
        except Exception as e:
            _logger.error(f"❌ Error al parsear JSON: {e} | Respuesta: {data_response.text[:1000]}")
            return

        if isinstance(data, dict) and "products" in data:
            product_list = data["products"]
        elif isinstance(data, list):
            product_list = data
        else:
            _logger.error("❌ El JSON descargado no es una lista ni tiene la clave 'products'. Revisa el formato del archivo.")
            return

        _logger.info(f"🔢 Se han recibido {len(product_list)} productos para procesar")

        # --- Atributos globales para variantes ---
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        for product in product_list:
            try:
                # Marca
                brand_data = product.get("brand") or {}
                brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""
                if not brand:
                    brand = "Sin Marca"
                brand_id = self.env['product.brand'].search([('name', '=', brand)], limit=1)
                if not brand_id:
                    brand_id = self.env['product.brand'].create({'name': brand})

                # Nombre, descripción
                name = product.get("designation", {}).get("es", product.get("catalogReference", "Sin Nombre"))
                description = product.get("description", {}).get("es", "")
                default_code = product.get("catalogReference", "")

                # Variantes
                colors = product.get("colors", [])
                all_sizes = set()
                all_colors = set()
                color_images = {}

                for color in colors:
                    color_name = color.get("colors", {}).get("es", "")
                    all_colors.add(color_name)
                    # Imagen FACE por color
                    face_url = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                    if color_name and face_url:
                        color_images[color_name] = face_url
                    for size in color.get("sizes", []):
                        all_sizes.add(size.get("size"))

                # Crear valores de atributo si faltan
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

                # Crea plantilla de producto
                template_vals = {
                    'name': name,
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                    'product_brand_id': brand_id.id if brand_id else False,
                }
                product_template = self.env['product.template'].create(template_vals)

                # Imagen principal
                images = product.get("images", [])
                main_image = None
                for img in images:
                    img_url = img.get("url_image", "")
                    if img_url:
                        main_image = get_image_binary_from_url(img_url)
                        break
                if main_image:
                    product_template.image_1920 = main_image

                # Recorrer variantes y asignar imagenes, codigos, precios (¡tendrás que implementar los requests de stock y precios!)
                for variant in product_template.product_variant_ids:
                    color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
                    color_name = color_val.name if color_val else ""
                    # Imagen variante por color
                    img_url = color_images.get(color_name)
                    if img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            variant.image_1920 = image_bin
                    # TODO: Asigna SKU, stock, precios aquí si tienes endpoints

                _logger.info(f"✅ Producto creado: {name}")

            except Exception as e:
                _logger.error(f"❌ Error procesando producto: {str(e)} | {json.dumps(product)[:500]}")