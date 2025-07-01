import json
import logging
import requests
import base64
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content)
    except Exception as e:
        _logger.warning(f"Error al descargar imagen desde {url}: {e}")
    return None

def get_toptex_token(proxy_url, username, password, api_key):
    url = f"{proxy_url}/v3/authenticate"
    payload = {"username": username, "password": password}
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("token")
        else:
            _logger.error(f"❌ Error autenticando con TopTex: {resp.text}")
    except Exception as e:
        _logger.error(f"❌ Error autenticando: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_catalog(self):
        # Lee parametros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key', '')
        username = icp.get_param('toptex_username', '')
        password = icp.get_param('toptex_password', '')
        proxy_url = icp.get_param('toptex_proxy_url', 'https://toptex-proxy.onrender.com')

        # Obtén token dinámicamente
        token = get_toptex_token(proxy_url, username, password, api_key)
        if not token:
            raise UserError("No se pudo autenticar con TopTex.")

        api_url = f"{proxy_url}/v3/products/all/?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        resp = requests.get(api_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.error(f"❌ Error al obtener link de catálogo: {resp.text}")
            raise UserError("No se pudo obtener el link de catálogo TopTex.")
        link = resp.json().get("link", "")
        if not link:
            _logger.error("❌ No se encontró el campo link en la respuesta de TopTex.")
            raise UserError("No se encontró el link de catálogo TopTex.")

        catalog_response = requests.get(link, timeout=300)
        if catalog_response.status_code != 200:
            _logger.error(f"❌ Error al descargar el JSON del catálogo: {catalog_response.text}")
            raise UserError("No se pudo descargar el JSON del catálogo TopTex.")
        catalog = catalog_response.json().get("products") or catalog_response.json().get("items") or catalog_response.json()
        if isinstance(catalog, dict):
            catalog = [catalog]

        count_total, count_error = 0, 0
        for prod in catalog:
            try:
                # Marca
                brand_name = prod.get("brand", {}).get("name", "") or "Sin Marca"
                brand = self.env["product.brand"].search([("name", "=", brand_name)], limit=1)
                if not brand:
                    brand = self.env["product.brand"].create({"name": brand_name})

                # Categoría
                categ_name = prod.get("category", {}).get("name", "") or "Sin Categoría"
                categ = self.env["product.category"].search([("name", "=", categ_name)], limit=1)
                if not categ:
                    categ = self.env["product.category"].create({"name": categ_name})

                # Atributos Color/Talla
                attr_color = self.env["product.attribute"].search([("name", "ilike", "color")], limit=1)
                if not attr_color:
                    attr_color = self.env["product.attribute"].create({"name": "Color"})
                attr_size = self.env["product.attribute"].search([("name", "ilike", "talla")], limit=1)
                if not attr_size:
                    attr_size = self.env["product.attribute"].create({"name": "Talla"})

                attribute_lines = []
                colors = prod.get("colors", [])
                sizes = set()
                color_values = []
                for color in colors:
                    color_name = color.get("color", {}).get("name", "").strip()
                    if color_name:
                        value_color = self.env["product.attribute.value"].search([
                            ("name", "=", color_name), ("attribute_id", "=", attr_color.id)
                        ], limit=1)
                        if not value_color:
                            value_color = self.env["product.attribute.value"].create({
                                "name": color_name, "attribute_id": attr_color.id
                            })
                        color_values.append(value_color.id)
                        for sz in color.get("sizes", []):
                            sizes.add(sz.get("size", "").strip())

                size_values = []
                for sz in sizes:
                    if sz:
                        value_size = self.env["product.attribute.value"].search([
                            ("name", "=", sz), ("attribute_id", "=", attr_size.id)
                        ], limit=1)
                        if not value_size:
                            value_size = self.env["product.attribute.value"].create({
                                "name": sz, "attribute_id": attr_size.id
                            })
                        size_values.append(value_size.id)

                if color_values:
                    attribute_lines.append((0, 0, {"attribute_id": attr_color.id, "value_ids": [(6, 0, color_values)]}))
                if size_values:
                    attribute_lines.append((0, 0, {"attribute_id": attr_size.id, "value_ids": [(6, 0, size_values)]}))

                # Datos producto
                default_code = prod.get("catalog_reference", "") or prod.get("catalogReference", "")
                description = prod.get("description", "")
                name = prod.get("name", "") or prod.get("designation", "")

                # Imagen principal SOLO la primera de la primera variante (para plantilla, no por variantes)
                image_url = ""
                if colors and colors[0].get("packshots", []):
                    image_url = colors[0]["packshots"][0].get("FACE", {}).get("urlPackshot", "")

                vals = {
                    "name": name,
                    "default_code": default_code,
                    "description": description,
                    "categ_id": categ.id,
                    "brand_id": brand.id,
                    "attribute_line_ids": attribute_lines,
                }
                if image_url:
                    image_bin = get_image_binary_from_url(image_url)
                    if image_bin:
                        vals["image_1920"] = image_bin

                template = self.env["product.template"].search([("default_code", "=", default_code)], limit=1)
                if not template:
                    template = self.env["product.template"].create(vals)
                    _logger.info(f"✅ Producto {default_code} creado.")
                else:
                    template.write(vals)
                    _logger.info(f"✅ Producto {default_code} actualizado.")

                count_total += 1

            except Exception as e:
                count_error += 1
                _logger.error(f"❌ Error importando producto: {e}")

        _logger.info(f"--- FIN: Total productos importados: {count_total}, errores: {count_error} ---")

    @api.model
    def sync_toptex_stock(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key', '')
        username = icp.get_param('toptex_username', '')
        password = icp.get_param('toptex_password', '')
        proxy_url = icp.get_param('toptex_proxy_url', 'https://toptex-proxy.onrender.com')

        token = get_toptex_token(proxy_url, username, password, api_key)
        if not token:
            raise UserError("No se pudo autenticar con TopTex.")

        inventory_url = f"{proxy_url}/v3/products/inventory?result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        resp = requests.get(inventory_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.error(f"❌ Error al pedir inventario: {resp.text}")
            raise UserError("No se pudo obtener el inventario TopTex.")
        link = resp.json().get("link", "")
        if not link:
            _logger.error("❌ No se encontró el campo link en la respuesta de inventario TopTex.")
            raise UserError("No se encontró el link de inventario TopTex.")

        inv_response = requests.get(link, timeout=300)
        if inv_response.status_code != 200:
            _logger.error(f"❌ Error al descargar el JSON del inventario: {inv_response.text}")
            raise UserError("No se pudo descargar el JSON del inventario TopTex.")
        inventory = inv_response.json().get("items") or inv_response.json().get("products") or inv_response.json()
        if isinstance(inventory, dict):
            inventory = [inventory]

        count_stock = 0
        ProductProduct = self.env['product.product']
        StockQuant = self.env['stock.quant']
        for item in inventory:
            sku = item.get("sku") or item.get("SKU") or item.get("reference", "")
            qty = sum([w.get("stock", 0) for w in item.get("warehouses", [])]) if item.get("warehouses") else item.get("stock", 0)
            product = ProductProduct.search([('default_code', '=', sku)], limit=1)
            if product:
                quants = StockQuant.search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ])
                if quants:
                    for quant in quants:
                        quant.inventory_quantity = qty
                        quant.quantity = qty
                    count_stock += 1
                    _logger.info(f"📦 Stock actualizado SKU {sku}: {qty}")
                else:
                    _logger.warning(f"❌ No stock.quant para SKU {sku}")
            else:
                _logger.warning(f"❌ Variante SKU {sku} no encontrada para stock.")
        _logger.info(f"🏁 FIN actualización stock. {count_stock} variantes actualizadas.")

    @api.model
    def sync_toptex_variant_images(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('toptex_api_key', '')
        username = icp.get_param('toptex_username', '')
        password = icp.get_param('toptex_password', '')
        proxy_url = icp.get_param('toptex_proxy_url', 'https://toptex-proxy.onrender.com')

        token = get_toptex_token(proxy_url, username, password, api_key)
        if not token:
            raise UserError("No se pudo autenticar con TopTex.")

        api_url = f"{proxy_url}/v3/products/all/?usage_right=b2b_b2c&display_prices=1&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }
        resp = requests.get(api_url, headers=headers, timeout=60)
        if resp.status_code != 200:
            _logger.error(f"❌ Error al pedir link de catálogo: {resp.text}")
            raise UserError("No se pudo obtener el link de catálogo TopTex para imágenes.")
        link = resp.json().get("link", "")
        if not link:
            _logger.error("❌ No se encontró el campo link en la respuesta de TopTex.")
            raise UserError("No se encontró el link de catálogo TopTex.")

        catalog_response = requests.get(link, timeout=300)
        if catalog_response.status_code != 200:
            _logger.error(f"❌ Error al descargar el JSON del catálogo: {catalog_response.text}")
            raise UserError("No se pudo descargar el JSON del catálogo TopTex.")
        catalog = catalog_response.json().get("products") or catalog_response.json().get("items") or catalog_response.json()
        if isinstance(catalog, dict):
            catalog = [catalog]

        ProductProduct = self.env['product.product']
        count_img = 0
        for prod in catalog:
            colors = prod.get("colors", [])
            for color in colors:
                img_url = ""
                if color.get("packshots"):
                    img_url = color["packshots"][0].get("FACE", {}).get("urlPackshot", "")
                for sz in color.get("sizes", []):
                    sku = sz.get("sku") or sz.get("SKU") or sz.get("reference", "")
                    variant = ProductProduct.search([('default_code', '=', sku)], limit=1)
                    if variant and img_url:
                        img = get_image_binary_from_url(img_url)
                        if img:
                            variant.image_1920 = img
                            count_img += 1
                            _logger.info(f"🖼 Imagen asignada SKU {sku}")
        _logger.info(f"🏁 FIN asignación imágenes por variante. {count_img} variantes actualizadas.")