# -*- coding: utf-8 -*-
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
            return base64.b64encode(buffer.getvalue())
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

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        headers["x-toptex-authorization"] = token

        offset = 0
        limit = 50
        existing_refs = set(self.env['product.template'].search([]).mapped('default_code'))

        while True:
            product_url = f"{proxy_url}/v3/products/all?offset={offset}&limit={limit}&usage_right=b2b_b2c"
            resp = requests.get(product_url, headers=headers)
            if resp.status_code != 200:
                _logger.warning(f"❌ Error en batch offset={offset}: {resp.text}")
                break

            batch = resp.json()
            if not batch:
                _logger.info(f"✅ Sin productos nuevos en este lote, fin de proceso.")
                break

            if isinstance(batch, dict) and "items" in batch:
                batch = batch["items"]

            any_valid = False

            for data in batch:
                catalog_ref = data.get("catalogReference")
                if not catalog_ref or catalog_ref in existing_refs:
                    _logger.info(f"⏩ Producto ya existe o sin referencia: {catalog_ref}")
                    continue

                any_valid = True

                brand = catalog_ref
                name_data = data.get("designation", {})
                name = name_data.get("es") or name_data.get("en") or "Producto sin nombre"
                name = name.replace("TopTex", "").strip()
                full_name = f"{catalog_ref} {name}".strip()

                description = data.get("description", {}).get("es", "") or data.get("description", {}).get("en", "")
                colors = data.get("colors", [])

                all_sizes = set()
                all_colors = set()
                for color in colors:
                    c_name = color.get("colors", {}).get("es", "") or color.get("colors", {}).get("en", "")
                    if not c_name:
                        continue
                    all_colors.add(c_name)
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
                    {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_vals.values()])]},
                    {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_vals.values()])]}
                ]

                template_vals = {
                    'name': full_name,
                    'default_code': catalog_ref,
                    'type': 'consu',
                    'is_storable': True,
                    'description_sale': description,
                    'categ_id': self.env.ref("product.product_category_all").id,
                    'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
                }

                try:
                    template = self.create(template_vals)
                    _logger.info(f"✅ Producto creado: {catalog_ref}")
                    existing_refs.add(catalog_ref)
                except Exception as e:
                    _logger.error(f"❌ Error creando producto {catalog_ref}: {str(e)}")
                    continue

                try:
                    for img in data.get("images", []):
                        img_url = img.get("url_image")
                        if img_url:
                            image_bin = get_image_binary_from_url(img_url)
                            if image_bin:
                                template.image_1920 = image_bin
                                break
                except Exception as e:
                    _logger.warning(f"⚠️ Imagen no asignada: {catalog_ref} - {str(e)}")

                try:
                    price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"
                    price_data = requests.get(price_url, headers=headers).json().get("items", [])

                    inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
                    inventory_items = requests.get(inv_url, headers=headers).json().get("items", [])

                    def get_price(color, size):
                        for item in price_data:
                            if item.get("color") == color and item.get("size") == size:
                                prices = item.get("prices", [])
                                if prices:
                                    return float(prices[0].get("price", 0.0))
                        return 0.0

                    def get_sku(color, size):
                        for item in inventory_items:
                            if item.get("color") == color and item.get("size") == size:
                                return item.get("sku")
                        return ""

                    for variant in template.product_variant_ids:
                        color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id).name
                        size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == size_attr.id).name
                        variant.default_code = get_sku(color, size)
                        variant.standard_price = get_price(color, size)
                        variant.lst_price = round(variant.standard_price * 2, 2) if variant.standard_price else 9.99

                except Exception as e:
                    _logger.warning(f"⚠️ Error en precios/SKUs: {catalog_ref} - {str(e)}")

            if not any_valid:
                _logger.info(f"✅ Lote offset={offset}, sin productos nuevos.")
                break

            offset += limit

    def sync_stock_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers).json().get("token")
        headers["x-toptex-authorization"] = token

        templates = self.search([("default_code", "!=", False)])
        StockQuant = self.env['stock.quant']

        for template in templates:
            inv_url = f"{proxy_url}/v3/products/inventory?catalog_reference={template.default_code}"
            inventory_items = requests.get(inv_url, headers=headers).json().get("items", [])

            for item in inventory_items:
                sku = item.get("sku")
                stock = sum(w.get("stock", 0) for w in item.get("warehouses", []))
                variant = template.product_variant_ids.filtered(lambda v: v.default_code == sku)
                if variant:
                    quant = StockQuant.search([
                        ('product_id', '=', variant.id),
                        ('location_id.usage', '=', 'internal')
                    ], limit=1)
                    if quant:
                        quant.quantity = stock
                        quant.inventory_quantity = stock
                        _logger.info(f"📦 Stock actualizado: {sku} = {stock}")

    def sync_variant_images_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        proxy_url = icp.get_param('toptex_proxy_url')
        api_key = icp.get_param('toptex_api_key')
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')

        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        token = requests.post(auth_url, json={"username": username, "password": password}, headers=headers).json().get("token")
        headers["x-toptex-authorization"] = token

        templates = self.search([("default_code", "!=", False)])

        for template in templates:
            url = f"{proxy_url}/v3/products?catalog_reference={template.default_code}&usage_right=b2b_b2c"
            data = requests.get(url, headers=headers).json()
            data = data[0] if isinstance(data, list) else data

            color_imgs = {
                c.get("colors", {}).get("es"): c.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for c in data.get("colors", [])
            }

            for variant in template.product_variant_ids:
                color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name.lower() == 'color')
                color = color_val.name if color_val else ""
                url_img = color_imgs.get(color)
                if url_img:
                    image_bin = get_image_binary_from_url(url_img)
                    if image_bin:
                        variant.image_1920 = image_bin
                        _logger.info(f"🖼️ Imagen variante: {variant.default_code}")