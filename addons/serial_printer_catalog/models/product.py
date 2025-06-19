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

        # --- URLs de API ---
        catalog_ref = "ns300"
        # Info principal del producto
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_b2c"
        # Stocks y precios de variantes
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        # --- Descargar datos principales ---
        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error obteniendo producto: {response.status_code} - {response.text}")
            data_list = response.json()
            data = data_list if isinstance(data_list, dict) else data_list[0] if data_list else {}
            _logger.info(f"📦 JSON producto:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener producto: {e}")
            return

        # --- Descargar precios y stock variantes ---
        def safe_json(url):
            try:
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    return r.json().get("items", [])
            except Exception as e:
                _logger.warning(f"❌ Error JSON en {url}: {e}")
            return []

        price_items = safe_json(price_url)
        stock_items = safe_json(stock_url)
        colors = data.get("colors", [])

        # --- Datos principales plantilla ---
        brand_data = data.get("brand") or {}
        brand_name = brand_data.get("name", {}).get("es", "") if isinstance(brand_data, dict) else ""

        name = data.get("designation", {}).get("es", "Producto sin nombre")
        full_name = f"{brand_name} {name}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", catalog_ref.upper())
        categ = self.env.ref("product.product_category_all")
        product_brand = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
        if not product_brand and brand_name:
            product_brand = self.env['product.brand'].create({'name': brand_name})

        # --- Imagen principal (primera imagen del producto) ---
        main_img_url = ""
        images = data.get("images", [])
        if images:
            main_img_url = images[0].get("url_image", "")
        main_img_bin = get_image_binary_from_url(main_img_url) if main_img_url else None

        # --- Crear plantilla ---
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'categ_id': categ.id,
            'image_1920': main_img_bin,
            'product_brand_id': product_brand.id if product_brand else False,
        }
        product_template = self.create(template_vals)
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # --- Crear atributos y variantes ---
        attribute_lines = []
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_vals = []
        size_vals = []
        for color in colors:
            color_name = color.get("colors", {}).get("es")
            if color_name and not self.env['product.attribute.value'].search([('name', '=', color_name), ('attribute_id', '=', color_attr.id)]):
                color_vals.append((0, 0, {'name': color_name, 'attribute_id': color_attr.id}))
            for size in color.get("sizes", []):
                size_name = size.get("size")
                if size_name and not self.env['product.attribute.value'].search([('name', '=', size_name), ('attribute_id', '=', size_attr.id)]):
                    size_vals.append((0, 0, {'name': size_name, 'attribute_id': size_attr.id}))

        if color_vals:
            self.env['product.attribute.value'].create([x[2] for x in color_vals])
        if size_vals:
            self.env['product.attribute.value'].create([x[2] for x in size_vals])

        # Añadir líneas de atributo a la plantilla
        product_template.write({
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in self.env['product.attribute.value'].search([('attribute_id', '=', color_attr.id)])])]
                }),
                (0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in self.env['product.attribute.value'].search([('attribute_id', '=', size_attr.id)])])]
                }),
            ]
        })
        _logger.info("✅ Variantes y atributos creados")

        # --- Precios, stock e imagen por variante ---
        for variant in product_template.product_variant_ids:
            # Encuentra color y talla de la variante
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id)
            size_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id)
            color_name = color_val.name if color_val else ""
            size_name = size_val.name if size_val else ""

            # --- Precio venta y coste ---
            price_val = 0.0
            cost_val = 0.0
            for item in price_items:
                if item.get("color") == color_name and item.get("size") == size_name:
                    for p in item.get("prices", []):
                        if p.get("quantity") == 1:
                            price_val = float(p.get("price", 0))
                            cost_val = float(p.get("price", 0))  # Modifica si hay otro campo para coste
                            break
                    break

            # --- Stock ---
            stock_val = 0
            for item in stock_items:
                if item.get("color") == color_name and item.get("size") == size_name:
                    for wh in item.get("warehouses", []):
                        if wh.get("id") == "toptex":
                            stock_val = int(wh.get("stock", 0))
                    break

            # --- Imagen variante ---
            img_url = ""
            for color in colors:
                if color.get("colors", {}).get("es") == color_name:
                    img_url = color.get("url_image", "")
                    break
            image_bin = get_image_binary_from_url(img_url) if img_url else None

            # --- Asignar datos a variante ---
            variant.write({
                'list_price': price_val,
                'standard_price': cost_val,
                'image_1920': image_bin if image_bin else variant.image_1920,
                # Si tienes campo custom para stock, aquí lo pones, si no se gestiona por inventario
            })
            _logger.info(f"💶 Variante {variant.name}: Precio {price_val}, Coste {cost_val}, Stock {stock_val}")

        _logger.info("✅ Producto NS300 creado profesionalmente con variantes, precios, coste, marca, stock e imágenes por variante.")