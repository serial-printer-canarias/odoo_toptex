import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# -------------------------------
# Utilidad para descargar imágenes
# -------------------------------
def get_image_binary_from_url(url):
    try:
        _logger.info(f"🖼️ Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
        else:
            _logger.warning(f"⚠️ No es imagen válida: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error procesando imagen: {url}: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------
    # 1. CREAR PRODUCTO + VARIANTES
    # -------------------------------
    @api.model
    def sync_product_ns300(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan parámetros TopTex en Sistema.")

        # 1. Login para TOKEN
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers, timeout=10)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ Token vacío.")

        # 2. GET Producto completo
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        response = requests.get(product_url, headers=headers, timeout=15)
        if response.status_code != 200:
            raise UserError(f"❌ Error obteniendo producto: {response.text}")
        data = response.json()
        if isinstance(data, list):
            data = data[0]  # Por si acaso devuelve array

        # MARCA, nombre y descripción
        brand = (data.get("brand", {}) or {}).get("name", {}).get("es", "") if isinstance(data.get("brand", {}), dict) else ""
        name = data.get("designation", {}).get("es", "NS300 sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # VARIANTES: colores y tallas
        colors = data.get("colors", [])
        all_colors = set()
        all_sizes = set()
        for color in colors:
            color_name = color.get("colors", {}).get("es", "")
            all_colors.add(color_name)
            for size in color.get("sizes", []):
                all_sizes.add(size.get("size"))

        # ATRIBUTOS en Odoo
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        # VALORES de atributos
        color_vals = {}
        for c in all_colors:
            v = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
            if not v:
                v = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
            color_vals[c] = v
        size_vals = {}
        for s in all_sizes:
            v = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
            if not v:
                v = self.env['product.attribute.value'].create({'name': s, 'attribute_id': size_attr.id})
            size_vals[s] = v

        attribute_lines = [
            {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
            {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])],
        }]

        # CREAR plantilla producto (SOLO CAMPOS BASE)
        product_template = self.create({
            'name': f"{brand} {name}".strip(),
            'default_code': default_code,
            'type': 'consu',  # Recuerda, solo consu + is_storable para stock
            'is_storable': True,
            'description_sale': description,
            'categ_id': self.env.ref("product.product_category_all").id,
            'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
        })
        _logger.info(f"✅ Producto creado: {product_template.name} (ID {product_template.id})")

    # ---------------------------------
    # 2. IMÁGENES por VARIANTE (APARTE)
    # ---------------------------------
    def sync_images_by_variant(self):
        # Recoge config y login fresco
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales TopTex.")
            return

        # Token nuevo por seguridad
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json={"username": username, "password": password}, headers=auth_headers, timeout=10)
        token = auth_response.json().get("token")
        if not token:
            _logger.error("❌ Sin token para imágenes variantes.")
            return

        # Llama API para obtener JSON completo
        product_url = f"{proxy_url}/v3/products?catalog_reference={self.default_code}&usage_right=b2b_b2c"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        response = requests.get(product_url, headers=headers, timeout=15)
        if response.status_code != 200:
            _logger.error(f"❌ Error obteniendo producto para imágenes por variantes: {response.text}")
            return
        data = response.json()
        if isinstance(data, list):
            data = data[0]
        colors = data.get("colors", [])

        # Mapeo de imagen por variante Odoo
        for variant in self.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
            # Busca el color correcto en JSON
            color_data = next((c for c in colors if c.get("colors", {}).get("es") == color), None)
            if color_data:
                packshots = color_data.get("packshots", {})
                img_url = None
                # PRIORIDAD: FACE > BACK > SIDE
                for key in ["FACE", "BACK", "SIDE"]:
                    img = packshots.get(key, {})
                    if img.get("url_packshot"):
                        img_url = img["url_packshot"]
                        break
                if img_url:
                    image_bin = get_image_binary_from_url(img_url)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🟦 Imagen asignada a variante {variant.name} desde {img_url}")

    # ---------------------------------
    # 3. STOCK por VARIANTE (APARTE)
    # ---------------------------------
    def sync_stock_by_variant(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales para stock.")
            return

        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json={"username": username, "password": password}, headers=auth_headers, timeout=10)
        token = auth_response.json().get("token")
        if not token:
            _logger.error("❌ Sin token para stock variantes.")
            return

        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}
        inv_resp = requests.get(inventory_url, headers=headers, timeout=10)
        if inv_resp.status_code != 200:
            _logger.error(f"❌ Error obteniendo inventario: {inv_resp.text}")
            return
        inventory_data = inv_resp.json().get("items", [])

        for variant in self.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "color").name
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == "talla").name
            stock = 0
            for item in inventory_data:
                if item.get("color") == color and item.get("size") == size:
                    stock = item.get("stock", 0)
                    break
            variant.qty_available = stock
            _logger.info(f"🟩 Variante: {variant.name} | Stock: {stock}")