import json
import logging
import requests
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }
        auth_headers = {
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando en TopTex: {auth_response.status_code} - {auth_response.text}")
            token_data = auth_response.json()
            token = token_data.get("token")
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("🔐 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # 2. Llamada con catalog_reference + b2b_b2c
        product_url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")
            data_list = response.json()
            if not isinstance(data_list, list) or not data_list:
                raise UserError("⚠️ Respuesta vacía o incorrecta.")
            data = data_list[0]
            _logger.info(f"📦 Producto NS300 recibido:\n{json.dumps(data, indent=2)}")
        except Exception as e:
            _logger.error(f"❌ Error en llamada a la API: {e}")
            return

        # 3. Crear product.template
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")
        list_price = 9.8

        product_template = self.create({
            'name': name,
            'default_code': default_code,
            'type': 'product',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': list_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        })
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # 4. Crear atributos y valores si no existen
        def get_or_create_attribute(name, value):
            attr = self.env['product.attribute'].search([('name', '=', name)], limit=1)
            if not attr:
                attr = self.env['product.attribute'].create({'name': name})
            val = self.env['product.attribute.value'].search([
                ('name', '=', value),
                ('attribute_id', '=', attr.id)
            ], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({
                    'name': value,
                    'attribute_id': attr.id
                })
            return attr, val

        # 5. Crear variantes (product.product)
        for color in data.get("colors", []):
            color_name = color.get("colors", {}).get("es")
            for size in color.get("sizes", []):
                size_name = size.get("size")
                sku = size.get("sku")
                ean = size.get("ean")
                price = size.get("publicUnitPrice", "9.8").replace(",", ".")

                color_attr, color_val = get_or_create_attribute("Color", color_name)
                size_attr, size_val = get_or_create_attribute("Talla", size_name)

                self.env['product.product'].create({
                    'product_tmpl_id': product_template.id,
                    'default_code': sku,
                    'barcode': ean,
                    'lst_price': float(price),
                    'attribute_value_ids': [(6, 0, [color_val.id, size_val.id])]
                })
                _logger.info(f"🧬 Variante: {color_name} / {size_name} - {sku}")

        # 6. Imagen principal
        img_url = data.get("images", [])[0].get("url_image") if data.get("images") else None
        if img_url:
            try:
                image_content = requests.get(img_url).content
                product_template.image_1920 = image_content
                _logger.info(f"🖼️ Imagen principal cargada desde: {img_url}")
            except Exception as e:
                _logger.warning(f"⚠️ No se pudo cargar imagen: {e}")