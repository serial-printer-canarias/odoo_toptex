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
        base_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not all([base_url, username, password, api_key]):
            raise UserError("Faltan parámetros del sistema.")

        # 🔐 Autenticación
        auth_url = f"{base_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }
        auth_headers = {"Content-Type": "application/json"}
        auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticación: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get('token')
        _logger.info(f"🔐 Token recibido: {token}")

        # 📦 Llamada a producto por catalog_reference
        headers = {
            "toptex-authorization": token,
            "Content-Type": "application/json"
        }
        url = f"{base_url}/v3/products?catalog_reference=ns300&usage_right=b2b_b2c"
        _logger.info(f"📡 Llamada GET a: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"❌ Error obteniendo producto: {response.status_code} - {response.text}")

        data_list = response.json()
        if not isinstance(data_list, list) or not data_list:
            raise UserError("⚠️ La respuesta no contiene datos de producto.")
        data = data_list[0]
        _logger.info(f"📦 JSON recibido:\n{json.dumps(data, indent=2)}")

        # 🛠️ Crear plantilla del producto
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        list_price = 9.8
        product_template = self.create({
            'name': name,
            'default_code': data.get("catalogReference"),
            'type': 'product',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': list_price,
            'categ_id': self.env.ref("product.product_category_all").id,
        })
        _logger.info(f"✅ Plantilla creada: {product_template.name}")

        # 🧬 Atributos
        def get_or_create_attribute(name, value):
            attr = self.env['product.attribute'].search([('name', '=', name)], limit=1)
            if not attr:
                attr = self.env['product.attribute'].create({'name': name})
            val = self.env['product.attribute.value'].search([
                ('name', '=', value), ('attribute_id', '=', attr.id)
            ], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({
                    'name': value, 'attribute_id': attr.id
                })
            return attr, val

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

        # 🖼️ Imagen principal
        img_url = data.get("images", [])[0].get("url_image") if data.get("images") else None
        if img_url:
            try:
                image_content = requests.get(img_url).content
                product_template.image_1920 = image_content
                _logger.info(f"🖼️ Imagen asignada desde: {img_url}")
            except Exception as e:
                _logger.warning(f"⚠️ Error imagen: {e}")