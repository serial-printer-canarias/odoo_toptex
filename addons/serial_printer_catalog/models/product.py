import base64
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models, fields, api, tools

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        IrConfig = self.env['ir.config_parameter'].sudo()

        proxy_url = IrConfig.get_param('toptex_proxy_url')
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')
        catalog_ref = 'NS300'

        if not all([proxy_url, username, password, api_key]):
            _logger.error("Faltan parámetros del sistema.")
            return

        # AUTENTICACIÓN
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        auth_payload = {'username': username, 'password': password}
        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        token = auth_response.json().get("token")

        if not token:
            _logger.error("Error al autenticar con TopTex.")
            return

        headers = {
            'x-api-key': api_key,
            'x-toptex-authorization': token,
            'Content-Type': 'application/json'
        }

        # LLAMADA PRINCIPAL AL PRODUCTO
        product_url = f"{proxy_url}/v3/products/{catalog_ref}?usage_right=b2b_uniquement"
        r = requests.get(product_url, headers=headers)
        if r.status_code != 200:
            _logger.error("No se pudo obtener el producto.")
            return

        data = r.json()
        _logger.info(f"Producto recibido: {data}")

        # LLAMADAS ADICIONALES
        stock_url = f"{proxy_url}/v3/products/inventory?catalog_reference={catalog_ref}"
        price_url = f"{proxy_url}/v3/products/price?catalog_reference={catalog_ref}"

        stock_data = requests.get(stock_url, headers=headers).json()
        price_data = requests.get(price_url, headers=headers).json()

        stock_total = stock_data[0].get("stock", 0) if isinstance(stock_data, list) and stock_data else 0
        standard_price = price_data[0].get("costPrice", 0.0) if isinstance(price_data, list) and price_data else 0.0

        # CAMPOS GENERALES
        name = f"{data.get('brand', {}).get('name', {}).get('es', '')} {data.get('translatedName', {}).get('es', '')}"
        description = data.get("description", {}).get("es", "")
        default_code = data.get("reference", catalog_ref)
        brand_name = data.get('brand', {}).get('name', {}).get('es', 'Sin marca')
        list_price = 10.0  # Precio venta fijo de momento
        categ_id = self.env.ref('product.product_category_all').id

        # IMAGEN PRINCIPAL
        main_img_url = data.get("images", {}).get("cover", {}).get("url", "")
        image_1920 = False
        if main_img_url:
            try:
                img_response = requests.get(main_img_url, stream=True)
                if img_response.status_code == 200:
                    img = Image.open(BytesIO(img_response.content))
                    img_format = img.format if img.format else 'PNG'
                    buffer = BytesIO()
                    img.save(buffer, format=img_format)
                    image_1920 = base64.b64encode(buffer.getvalue())
            except Exception as e:
                _logger.warning(f"No se pudo cargar imagen principal: {e}")

        # MARCA
        brand_obj = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
        if not brand_obj:
            brand_obj = self.env['product.brand'].create({'name': brand_name})

        # PRODUCTO BASE
        product_template = self.env['product.template'].create({
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'list_price': list_price,
            'standard_price': standard_price,
            'description_sale': description,
            'image_1920': image_1920,
            'categ_id': categ_id,
            'product_brand_id': brand_obj.id,
        })

        # ATRIBUTOS Y VARIANTES
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_lines = []
        for color in data.get("colors", []):
            color_name = color.get("translatedName", {}).get("es")
            if not color_name:
                continue

            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name),
                ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })

            for size in color.get("sizes", []):
                size_name = size.get("translatedName", {}).get("es")
                if not size_name:
                    continue

                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name),
                    ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({
                        'name': size_name,
                        'attribute_id': size_attr.id
                    })

                variant = self.env['product.product'].create({
                    'product_tmpl_id': product_template.id,
                    'attribute_value_ids': [(6, 0, [color_val.id, size_val.id])],
                    'default_code': size.get("sku") or '',
                    'barcode': size.get("ean13") or '',
                })

                # IMAGEN POR VARIANTE
                color_img_url = color.get("images", {}).get("cover", {}).get("url", "")
                if color_img_url:
                    try:
                        img_response = requests.get(color_img_url, stream=True)
                        if img_response.status_code == 200:
                            img = Image.open(BytesIO(img_response.content))
                            buffer = BytesIO()
                            img.save(buffer, format=img.format or 'PNG')
                            variant.image_1920 = base64.b64encode(buffer.getvalue())
                    except Exception as e:
                        _logger.warning(f"Error en imagen variante {color_name}: {e}")