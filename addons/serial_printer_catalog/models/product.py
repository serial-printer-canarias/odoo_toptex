import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        _logger.info(f"📥 Descargando imagen desde {url}")
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        if image.mode in ("RGBA", "P"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()
        return base64.b64encode(image_bytes)
    except Exception as e:
        _logger.warning(f"❌ Error al procesar imagen desde {url}: {e}")
        return None

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def sync_products_from_api(self):
        # ---- CONFIG ----
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex.api_key', '')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex.api_token', '')
        catalog_url = "https://toptex-proxy.onrender.com/v3/products/all/?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }

        # ---- 1. PETICIÓN PRIMERA: DEVUELVE LINK AL JSON MASIVO ----
        res = requests.get(catalog_url, headers=headers)
        if res.status_code != 200:
            raise UserError(f"❌ Error al pedir link JSON catálogo: {res.text}")
        url_json = res.json().get("link")
        _logger.info(f"📝 Link JSON catálogo: {url_json}")

        # ---- 2. BAJA EL ARCHIVO MASIVO ----
        r_json = requests.get(url_json, timeout=60)
        if r_json.status_code != 200:
            raise UserError(f"❌ Error bajando JSON: {r_json.text}")

        catalog = r_json.json().get("items", [])
        _logger.info(f"🔎 Catálogo recibido: {len(catalog)} productos.")

        # ---- 3. MAPEAMOS Y CREAMOS PRODUCTOS ----
        count_ok = 0
        for prod in catalog:
            catalog_ref = prod.get("catalogReference", "")
            name = prod.get("name", "Sin nombre")
            brand_data = prod.get("brand", {})
            brand = brand_data.get("name", "Sin Marca")
            description = prod.get("description", "")
            category_name = prod.get("family", {}).get("name", "Sin familia")
            # -- Crea marca si no existe
            brand_id = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_id:
                brand_id = self.env['product.brand'].create({'name': brand})
            # -- Crea categoría si no existe
            categ_id = self.env['product.category'].search([('name', '=', category_name)], limit=1)
            if not categ_id:
                categ_id = self.env['product.category'].create({'name': category_name})

            # -- Extraemos colores y tallas para variantes
            colors = prod.get("colors", [])
            color_vals = []
            size_vals = set()
            for color in colors:
                color_name = color.get("color", {}).get("name", "Sin color")
                color_vals.append(color_name)
                for sz in color.get("sizes", []):
                    size_vals.add(sz.get("size", "Sin talla"))

            # -- Crea atributos Color y Talla si no existen
            attr_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not attr_color:
                attr_color = self.env['product.attribute'].create({'name': 'Color'})
            attr_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not attr_size:
                attr_size = self.env['product.attribute'].create({'name': 'Talla'})

            # -- Crea valores de atributos si faltan
            color_attr_vals = []
            for c in color_vals:
                v = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', attr_color.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].create({'name': c, 'attribute_id': attr_color.id})
                color_attr_vals.append(v.id)
            size_attr_vals = []
            for s in size_vals:
                v = self.env['product.attribute.value'].search([('name', '=', s), ('attribute_id', '=', attr_size.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].create({'name': s, 'attribute_id': attr_size.id})
                size_attr_vals.append(v.id)

            # -- Crea o actualiza producto padre
            template_vals = {
                'name': name,
                'default_code': catalog_ref,
                'categ_id': categ_id.id,
                'description': description,
                'is_storable': True,
                'brand_id': brand_id.id,
                'attribute_line_ids': [
                    (0, 0, {'attribute_id': attr_color.id, 'value_ids': [(6, 0, color_attr_vals)]}),
                    (0, 0, {'attribute_id': attr_size.id, 'value_ids': [(6, 0, size_attr_vals)]}),
                ]
            }
            template = self.env['product.template'].search([('default_code', '=', catalog_ref)], limit=1)
            if not template:
                template = self.env['product.template'].create(template_vals)
            else:
                template.write(template_vals)
            count_ok += 1

            # ---- IMAGEN PRINCIPAL (del primer color) ----
            image_url = ""
            if colors and colors[0].get("packshots", []):
                image_url = colors[0]["packshots"][0].get("urlPackshot", "")
            if image_url:
                img = get_image_binary_from_url(image_url)
                if img:
                    template.image_1920 = img

            _logger.info(f"✅ Producto {catalog_ref} creado/actualizado: {name} [{brand}]")

        _logger.info(f"🏁 Proceso terminado: {count_ok} productos creados/actualizados.")

    # ---- SERVER ACTION STOCK (Actualiza stock por variantes desde archivo masivo) ----
    @api.model
    def sync_stock_from_api(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex.api_key', '')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex.api_token', '')
        inventory_url = "https://api.toptex.io/v3/products/inventory/result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }
        res = requests.get(inventory_url, headers=headers)
        if res.status_code != 200:
            raise UserError(f"❌ Error al pedir inventario: {res.text}")
        url_json = res.json().get("link")
        r_json = requests.get(url_json, timeout=60)
        if r_json.status_code != 200:
            raise UserError(f"❌ Error bajando inventario JSON: {r_json.text}")
        items = r_json.json().get("items", [])
        count_ok = 0
        StockQuant = self.env['stock.quant']
        ProductProduct = self.env['product.product']
        for item in items:
            sku = item.get("sku")
            qty = item.get("stock", 0)
            variant = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if variant:
                quants = StockQuant.search([
                    ('product_id', '=', variant.id),
                    ('location_id.usage', '=', 'internal'),
                ])
                for quant in quants:
                    quant.inventory_quantity = qty
                    count_ok += 1
                _logger.info(f"📦 Stock actualizado SKU {sku}: {qty}")
            else:
                _logger.warning(f"❌ Variante SKU {sku} no encontrada para stock.")
        _logger.info(f"🏁 FIN actualización stock. {count_ok} variantes actualizadas.")

    # ---- SERVER ACTION IMÁGENES POR VARIANTE ----
    @api.model
    def sync_variant_images_from_api(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex.api_key', '')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex.api_token', '')
        catalog_url = "https://toptex-proxy.onrender.com/v3/products/all/?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
        }
        res = requests.get(catalog_url, headers=headers)
        if res.status_code != 200:
            raise UserError(f"❌ Error al pedir link JSON catálogo: {res.text}")
        url_json = res.json().get("link")
        r_json = requests.get(url_json, timeout=60)
        if r_json.status_code != 200:
            raise UserError(f"❌ Error bajando JSON: {r_json.text}")

        catalog = r_json.json().get("items", [])
        ProductProduct = self.env['product.product']
        count_img = 0
        for prod in catalog:
            colors = prod.get("colors", [])
            for color in colors:
                img_url = ""
                if color.get("packshots"):
                    img_url = color["packshots"][0].get("urlPackshot", "")
                for sz in color.get("sizes", []):
                    sku = sz.get("sku")
                    variant = ProductProduct.search([('default_code', '=', sku)], limit=1)
                    if variant and img_url:
                        img = get_image_binary_from_url(img_url)
                        if img:
                            variant.image_1920 = img
                            count_img += 1
                            _logger.info(f"🖼 Imagen asignada SKU {sku}")
        _logger.info(f"🏁 FIN asignación imágenes por variante. {count_img} variantes actualizadas.")