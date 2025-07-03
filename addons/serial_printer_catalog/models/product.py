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

        # --- AUTENTICACIÓN ---
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

        # --- CATALOGO ALL ---
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        catalog_response = requests.get(catalog_url, headers=headers)
        if catalog_response.status_code != 200:
            raise UserError(f"❌ Error al pedir el catálogo: {catalog_response.status_code} - {catalog_response.text}")

        file_link = catalog_response.json().get("link")
        if not file_link:
            raise UserError("❌ No se obtuvo el link del JSON de productos")
        json_response = requests.get(file_link, headers=headers)
        if json_response.status_code != 200:
            raise UserError(f"❌ Error descargando el JSON catálogo: {json_response.status_code} - {json_response.text}")

        catalog_data = json_response.json()
        catalog = catalog_data if isinstance(catalog_data, list) else catalog_data.get('items', catalog_data)
        _logger.info(f"🔄 Procesando {len(catalog)} productos Toptex...")

        brands_cache = {}
        count_products = 0

        for prod in catalog:
            default_code = prod.get('catalogReference', '') or prod.get('reference', '')
            brand_name = ""
            if isinstance(prod.get('brand'), dict):
                brand_name = prod['brand'].get('name', '') or prod['brand'].get('es', '') or ''
            else:
                brand_name = prod.get('brand', '')
            designation = prod.get('designation', {})
            name = designation.get('es') or designation.get('en') or ''
            description = prod.get('description', {}).get('es', '') or prod.get('description', {}).get('en', '')
            composition = prod.get('composition', {}).get('es', '') or ''
            gramaje = prod.get('averageWeight', '')
            argumentos = prod.get('salesArguments', {}).get('es', '') or ''
            main_materials = ", ".join([m.get("es", "") for m in prod.get("mainMaterials", []) if m.get("es")])
            pictos = ", ".join([p.get("es", "") for p in prod.get("pictograms", []) if p.get("es")])
            organic = ", ".join([o.get("es", "") for o in prod.get("organic", []) if o.get("es")])
            oeko_tex = prod.get("oekoTex", "")

            # --- MARCA ---
            if brand_name:
                if brand_name not in brands_cache:
                    brand_obj = self.env['product.brand'].sudo().search([('name', '=', brand_name)], limit=1)
                    if not brand_obj:
                        brand_obj = self.env['product.brand'].sudo().create({'name': brand_name})
                        _logger.info(f"➕ Marca creada: {brand_name}")
                    brands_cache[brand_name] = brand_obj
                else:
                    brand_obj = brands_cache[brand_name]
            else:
                brand_obj = False

            # --- CATEGORÍA ---
            cat_name = prod.get('category', '')
            categ_obj = self.env['product.category'].sudo().search([('name', '=', cat_name)], limit=1) if cat_name else False
            if not categ_obj:
                categ_obj = self.env['product.category'].sudo().search([('name', '=', 'All')], limit=1)
                if not categ_obj:
                    categ_obj = self.env['product.category'].sudo().create({'name': 'All'})

            # --- ATRIBUTOS COLOR/TALLA ---
            color_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].sudo().create({'name': 'Color'})
            size_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].sudo().create({'name': 'Talla'})

            # --- VALORES DE COLOR/TALLA ---
            color_vals, size_vals = set(), set()
            for color in prod.get('colors', []):
                c_name = color.get('colors', {}).get('es', '') or color.get('color', '')
                if c_name:
                    color_vals.add(c_name)
                for sz in color.get('sizes', []):
                    size_name = sz.get('size', '')
                    if size_name:
                        size_vals.add(size_name)
            color_val_objs = []
            for c in color_vals:
                v = self.env['product.attribute.value'].sudo().search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].sudo().create({'name': c, 'attribute_id': color_attr.id})
                color_val_objs.append(v.id)
            size_val_objs = []
            for s in size_vals:
                v = self.env['product.attribute.value'].sudo().search([('name', '=', s), ('attribute_id', '=', size_attr.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].sudo().create({'name': s, 'attribute_id': size_attr.id})
                size_val_objs.append(v.id)
            attribute_lines = [
                (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_val_objs)]}),
                (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, size_val_objs)]}),
            ]

            # --- CAMPOS EXTRA ---
            extra_vals = {
                'x_composicion': composition,
                'x_gramaje': gramaje,
                'x_argumentos': argumentos,
                'x_materiales': main_materials,
                'x_pictogramas': pictos,
                'x_certificado_organic': organic,
                'x_oeko_tex': oeko_tex,
            }

            # --- CREACIÓN/ACTUALIZACIÓN PLANTILLA ---
            template_vals = {
                'name': f"{brand_name} {name}",
                'default_code': default_code,
                'description_sale': description,
                'type': 'consu',
                'is_storable': True,
                'categ_id': categ_obj.id,
                'brand_id': brand_obj.id if brand_obj else False,
                'attribute_line_ids': attribute_lines,
            }
            template_vals.update(extra_vals)

            tmpl = self.env['product.template'].sudo().search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                tmpl = self.env['product.template'].sudo().create(template_vals)
                count_products += 1
                _logger.info(f"➕ Producto creado: {default_code}")
            else:
                tmpl.sudo().write(template_vals)
                _logger.info(f"🔄 Producto actualizado: {default_code}")

            # --- VARIANTES ---
            for color in prod.get('colors', []):
                color_name = color.get('colors', {}).get('es', '') or color.get('color', '')
                for sz in color.get('sizes', []):
                    size_name = sz.get('size', '')
                    sku = sz.get('sku', '')
                    precio_coste = sz.get('publicUnitPrice', 0.0)
                    ean = sz.get('ean', '')
                    variant = self.env['product.product'].sudo().search([
                        ('product_tmpl_id', '=', tmpl.id),
                        ('product_template_attribute_value_ids.attribute_id', '=', color_attr.id),
                        ('product_template_attribute_value_ids.name', '=', color_name),
                        ('product_template_attribute_value_ids.attribute_id', '=', size_attr.id),
                        ('product_template_attribute_value_ids.name', '=', size_name),
                    ], limit=1)
                    if variant:
                        variant.sudo().write({
                            'default_code': sku,
                            'standard_price': float(precio_coste) if precio_coste else 0.0,
                            'barcode': ean,
                        })
                        _logger.info(f"✅ Variante actualizada SKU: {sku}")
                    else:
                        _logger.warning(f"❌ Variante no encontrada para SKU: {sku}")

            # --- IMAGEN PRINCIPAL ---
            img_url = None
            if prod.get("images"):
                img_url = prod["images"][0].get("url_image", "")
            if not img_url and prod.get("colors"):
                color_first = prod["colors"][0]
                packshots = color_first.get("packshots", {})
                if "FACE" in packshots:
                    img_url = packshots["FACE"].get("url_packshot", "")
            if img_url:
                img_bin = get_image_binary_from_url(img_url)
                if img_bin:
                    tmpl.sudo().write({'image_1920': img_bin})
                    _logger.info(f"🖼️ Imagen principal asignada a {default_code}")

        _logger.info(f"✅ FIN: Asignación de {count_products} productos TopTex.")
        return True

    @api.model
    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # --- AUTENTICACIÓN ---
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para stock.")
            return

        # --- INVENTARIO GLOBAL ---
        inventory_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        inv_resp = requests.get(inventory_url, headers=headers)
        if inv_resp.status_code != 200:
            _logger.error("❌ Error al obtener inventario: " + inv_resp.text)
            return

        file_link = inv_resp.json().get("link", "")
        if not file_link:
            _logger.error("❌ No se obtuvo link de inventario")
            return
        stock_json = requests.get(file_link, headers=headers)
        if stock_json.status_code != 200:
            _logger.error("❌ Error descargando inventario: " + stock_json.text)
            return
        inventory_items = stock_json.json()
        if not isinstance(inventory_items, list):
            inventory_items = inventory_items.get("items", [])
        StockQuant = self.env['stock.quant']
        for item in inventory_items:
            sku = item.get("sku")
            stock = item.get("inventory", 0)
            if not sku:
                continue
            product = self.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
            if product:
                quants = StockQuant.sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ])
                if quants:
                    for quant in quants:
                        quant.sudo().inventory_quantity = stock
                        _logger.info(f"📦 Stock actualizado: {sku} = {stock}")
                else:
                    _logger.warning(f"❌ No hay stock.quant para {sku}")
            else:
                _logger.warning(f"❌ Variante no encontrada para SKU {sku}")

    @api.model
    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        # --- AUTENTICACIÓN ---
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        token = auth_resp.json().get("token")
        if not token:
            _logger.error("❌ Error autenticando para imágenes.")
            return

        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers.update({"x-toptex-authorization": token})
        catalog_response = requests.get(catalog_url, headers=headers)
        if catalog_response.status_code != 200:
            _logger.error(f"❌ Error obteniendo catálogo para imágenes: {catalog_response.text}")
            return
        file_link = catalog_response.json().get("link")
        if not file_link:
            _logger.error("❌ No se obtuvo el link del JSON de productos para imágenes")
            return
        json_response = requests.get(file_link, headers=headers)
        if json_response.status_code != 200:
            _logger.error(f"❌ Error descargando el JSON catálogo para imágenes: {json_response.text}")
            return
        catalog_data = json_response.json()
        catalog = catalog_data if isinstance(catalog_data, list) else catalog_data.get('items', catalog_data)
        count_img = 0

        for prod in catalog:
            for color in prod.get('colors', []):
                img_url = None
                packshots = color.get('packshots', {})
                if "FACE" in packshots:
                    img_url = packshots["FACE"].get("url_packshot", "")
                if not img_url:
                    continue
                for sz in color.get('sizes', []):
                    sku = sz.get('sku', '')
                    product = self.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
                    if product and img_url:
                        image_bin = get_image_binary_from_url(img_url)
                        if image_bin:
                            product.sudo().write({'image_1920': image_bin})
                            count_img += 1
                            _logger.info(f"🖼️ Imagen variante asignada a SKU: {sku}")
        _logger.info(f"✅ FIN asignación imágenes por variante ({count_img})")