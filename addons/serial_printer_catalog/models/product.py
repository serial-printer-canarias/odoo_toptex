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
        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("🔐 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Descarga info NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"📥 Respuesta cruda:\n{response.text}")
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
            data_list = response.json()
            data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
            _logger.info(f"📦 JSON interpretado:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto desde API: {e}")
            return

        # --- MARCA ---
        brand_data = data.get("brand") or {}
        brand = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        # --- PLANTILLA PRINCIPAL ---
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        # --- VARIANTES ---
        # Reunimos colores y tallas
        colors = data.get("colors", [])
        all_sizes = set()
        all_colors = set()
        for color in colors:
            color_name = color.get("colors", {}).get("es", "")
            all_colors.add(color_name)
            for size in color.get("sizes", []):
                all_sizes.add(size.get("size"))

        # Creamos atributos si no existen
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1) or self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1) or self.env['product.attribute'].create({'name': 'Talla'})

        # Creamos valores de atributos
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

        # Atributos para la plantilla
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
            'type': 'consu',  # No 'product', solo consu + is_storable para stock
            'is_storable': True,
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
        # Llamada a Precios para todas las variantes
        try:
            price_url = f"{proxy_url}/v3/products/price?catalog_reference=ns300"
            headers = {
                "x-api-key": api_key,
                "x-toptex-authorization": token
            }
            price_resp = requests.get(price_url, headers=headers)
            price_data = price_resp.json().get("items", []) if price_resp.status_code == 200 else []
        except Exception as e:
            _logger.error(f"❌ Error en precios: {e}")
            price_data = []

        def get_price_cost(color, size):
            for item in price_data:
                if item.get("color") == color and item.get("size") == size:
                    # Busca el precio de coste en el array "prices"
                    prices = item.get("prices", [])
                    if prices:
                        return float(prices[0].get("price", 0.0))
            return 0.0

        # --- DATOS PARA VARIANTES (coste, venta, SIN stock, SIN imagen) ---
        for variant in product_template.product_variant_ids:
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
            size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
            color_name = color_val.name if color_val else ""
            size_name = size_val.name if size_val else ""

            # --- Precios ---
            coste = get_price_cost(color_name, size_name)
            variant.standard_price = coste
            variant.lst_price = coste * 1.25 if coste > 0 else 9.8  # Margen ejemplo
            _logger.info(f"💰 Variante: {variant.name} | Coste: {coste}")

        _logger.info(f"✅ Producto NS300 creado y listo para ventas B2B/B2C en Odoo!")

    # ------ METODOS PARA AÑADIR STOCK Y FOTOS POR VARIANTE DESPUÉS (llama cuando quieras) ------
    def sync_stock_from_api(self):
        """
        Actualiza el stock de cada variante usando la API de TopTex.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        token = icp.get_param('toptex_token')  # Guarda el token donde prefieras
        if not all([api_key, proxy_url, token]):
            return

        inventory_url = f"{proxy_url}/v3/products/inventory?catalog_reference={self.default_code}"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        try:
            inv_resp = requests.get(inventory_url, headers=headers)
            if inv_resp.status_code == 200:
                inventory_data = inv_resp.json().get("items", [])
                for variant in self.product_variant_ids:
                    color = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.name.lower() == "color"
                    ).name
                    size = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.name.lower() == "talla"
                    ).name
                    stock = 0
                    for item in inventory_data:
                        if item.get("color") == color and item.get("size") == size:
                            stock = item.get("stock", 0)
                            break
                    variant.qty_available = stock
        except Exception as e:
            _logger.error(f"Error actualizando stock: {e}")

    def sync_images_by_variant(self):
        """
        Asigna imágenes a cada variante usando la API de TopTex.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        token = icp.get_param('toptex_token')
        if not all([api_key, proxy_url, token]):
            return

        product_url = f"{proxy_url}/v3/products?catalog_reference={self.default_code}"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code == 200:
                data_list = response.json()
                data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
                colors = data.get("colors", [])
                for variant in self.product_variant_ids:
                    color_name = variant.product_template_attribute_value_ids.filtered(
                        lambda v: v.attribute_id.name.lower() == "color"
                    ).name
                    color_data = next((c for c in colors if c.get("colors", {}).get("es") == color_name), None)
                    if color_data:
                        img_url = color_data.get("url_image", "")
                        if img_url:
                            image_bin = get_image_binary_from_url(img_url)
                            if image_bin:
                                variant.image_1920 = image_bin
        except Exception as e:
            _logger.error(f"Error asignando imagenes por variante: {e}")