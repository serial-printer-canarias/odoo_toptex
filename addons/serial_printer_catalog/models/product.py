import logging
import json
import requests
import base64
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def import_toptex_from_json(self, file_path='/home/odoo/src/user/addons/serial_printer_catalog/data/toptex_catalog.json'):
        """
        Lee el JSON local subido (ajusta path si es distinto) y crea plantillas con variantes (color y talla).
        NO añade stock, precios, ni imágenes. Solo estructura básica.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                products_data = json.load(f)
        except Exception as e:
            raise UserError(f"No se pudo abrir el JSON: {e}")

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        talla_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not talla_attr:
            talla_attr = self.env['product.attribute'].create({'name': 'Talla'})

        creados = 0
        for prod in products_data:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            colors = prod.get("colors", [])
            all_colors = set()
            all_tallas = set()
            for color in colors:
                color_name = color.get("colors", {}).get("es", "") or color.get("colorName", "")
                if color_name:
                    all_colors.add(color_name)
                for size in color.get("sizes", []):
                    talla = size.get("size", "")
                    if talla:
                        all_tallas.add(talla)
            # Valores de atributos
            color_val_objs = []
            for c in all_colors:
                val = self.env['product.attribute.value'].search([('name', '=', c), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': c, 'attribute_id': color_attr.id})
                color_val_objs.append(val)
            talla_val_objs = []
            for t in all_tallas:
                val = self.env['product.attribute.value'].search([('name', '=', t), ('attribute_id', '=', talla_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': t, 'attribute_id': talla_attr.id})
                talla_val_objs.append(val)
            attribute_lines = []
            if color_val_objs:
                attribute_lines.append({'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_val_objs])]})
            if talla_val_objs:
                attribute_lines.append({'attribute_id': talla_attr.id, 'value_ids': [(6, 0, [v.id for v in talla_val_objs])]})
            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, l) for l in attribute_lines],
            }
            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                creados += 1
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

        _logger.info(f"🚀 FIN: {creados} plantillas de producto creadas con variantes, color y talla (TopTex).")
        return f"Importados {creados} productos."

    # ---- MÉTODOS DE SERVER ACTION MANUAL ----

    def _toptex_auth(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')
        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales TopTex")
        url = f"{proxy_url}/v3/authenticate"
        headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        payload = {"username": username, "password": password}
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {response.status_code} - {response.text}")
        token = response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido Toptex")
        return token, api_key, proxy_url

    @api.model
    def manual_update_toptex_stock(self):
        token, api_key, proxy_url = self._toptex_auth()
        for product in self.search([]):
            for variant in product.product_variant_ids:
                sku = variant.default_code
                if not sku:
                    continue
                url = f"{proxy_url}/v3/products/stock?reference={sku}"
                headers = {
                    "x-api-key": api_key,
                    "x-toptex-authorization": token,
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    stock = response.json().get("stock", 0)
                    variant.qty_available = stock  # Cambia si usas otro campo de stock
                    _logger.info(f"Stock actualizado para {sku}: {stock}")
                else:
                    _logger.warning(f"No se pudo obtener stock para {sku}: {response.text}")

    @api.model
    def manual_update_toptex_prices(self):
        token, api_key, proxy_url = self._toptex_auth()
        for product in self.search([]):
            for variant in product.product_variant_ids:
                sku = variant.default_code
                if not sku:
                    continue
                url = f"{proxy_url}/v3/products/reference/{sku}"
                headers = {
                    "x-api-key": api_key,
                    "x-toptex-authorization": token,
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    jsondata = response.json()
                    try:
                        price = float(jsondata.get("prices", [{}])[0].get("price", 0.0))
                        variant.standard_price = price
                        variant.lst_price = round(price * 1.25, 2)
                        _logger.info(f"Precio actualizado para {sku}: {price}")
                    except Exception as e:
                        _logger.warning(f"Error leyendo precio para {sku}: {e}")
                else:
                    _logger.warning(f"No se pudo obtener precio para {sku}: {response.text}")

    @api.model
    def manual_update_toptex_images(self):
        token, api_key, proxy_url = self._toptex_auth()
        for product in self.search([]):
            for variant in product.product_variant_ids:
                sku = variant.default_code
                if not sku:
                    continue
                url = f"{proxy_url}/v3/products/reference/{sku}"
                headers = {
                    "x-api-key": api_key,
                    "x-toptex-authorization": token,
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    jsondata = response.json()
                    img_url = ""
                    packshots = jsondata.get("packshots", {})
                    if "FACE" in packshots:
                        img_url = packshots["FACE"].get("url_packshot", "")
                    elif "images" in jsondata:
                        img_url = jsondata["images"][0].get("url_image", "")
                    if img_url:
                        try:
                            img_bin = requests.get(img_url, timeout=15).content
                            variant.image_1920 = base64.b64encode(img_bin)
                            _logger.info(f"Imagen actualizada para {sku}")
                        except Exception as e:
                            _logger.warning(f"Error descargando imagen para {sku}: {e}")
                else:
                    _logger.warning(f"No se pudo obtener imagen para {sku}: {response.text}")