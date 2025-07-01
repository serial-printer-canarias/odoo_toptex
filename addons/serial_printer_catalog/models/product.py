import json
import logging
import requests
import base64
from PIL import Image
from io import BytesIO
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            image = Image.open(BytesIO(response.content)).convert("RGB")
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            img_str = base64.b64encode(buffer.getvalue())
            _logger.info(f"✅ Imagen descargada: {url}")
            return img_str
        else:
            _logger.warning(f"⚠️ Respuesta no válida de imagen: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error descargando imagen desde {url}: {e}")
    return False

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')

        if not all([api_key, username, password, proxy_url]):
            raise UserError('Faltan parámetros API TopTex')

        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_resp.status_code != 200:
            _logger.error(f"❌ Error autenticando TopTex: {auth_resp.text}")
            raise UserError(f"Error autenticando: {auth_resp.text}")
        token = auth_resp.json().get('token', '')
        if not token:
            raise UserError('No se recibió token TopTex')
        headers['x-toptex-authorization'] = token

        # ----------- DESCARGA MASIVA DEL CATALOGO COMPLETO -----------
        catalog_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1'
        cat_resp = requests.get(catalog_url, headers=headers)
        if cat_resp.status_code != 200:
            _logger.error(f"❌ Error obteniendo catálogo: {cat_resp.text}")
            raise UserError(f"Error obteniendo catálogo: {cat_resp.text}")
        file_link = cat_resp.json().get('link', '')
        if not file_link:
            raise UserError('No se obtuvo el link del JSON de productos')
        json_resp = requests.get(file_link, headers=headers)
        if json_resp.status_code != 200:
            raise UserError(f"Error descargando el JSON catálogo: {json_resp.text}")
        data = json_resp.json()
        catalog = data if isinstance(data, list) else data.get('items', data)
        count_products = 0
        brands_cache = {}

        for prod in catalog:
            brand_data = prod.get('brand', {})
            brand_name = brand_data.get('name', '').strip()
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

            cat_name = prod.get('category', '')
            if cat_name:
                categ_obj = self.env['product.category'].sudo().search([('name', '=', cat_name)], limit=1)
                if not categ_obj:
                    categ_obj = self.env['product.category'].sudo().create({'name': cat_name})
                    _logger.info(f"➕ Categoría creada: {cat_name}")
            else:
                categ_obj = self.env['product.category'].sudo().search([('name', '=', 'All')], limit=1)
                if not categ_obj:
                    categ_obj = self.env['product.category'].sudo().create({'name': 'All'})
            ref = prod.get('reference', '')
            name = prod.get('name', '') or 'Producto sin nombre'
            description = prod.get('description', '')
            colors = prod.get('colors', [])

            color_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].sudo().create({'name': 'Color'})
            size_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].sudo().create({'name': 'Talla'})

            color_vals, size_vals = set(), set()
            for color in colors:
                c_name = color.get('color', '')
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

            template_vals = {
                'name': name,
                'default_code': ref,
                'is_storable': True,
                'description': description,
                'categ_id': categ_obj.id,
                'brand_id': brand_obj.id if brand_obj else False,
                'attribute_line_ids': attribute_lines,
                'type': 'consu',
            }

            tmpl = self.env['product.template'].sudo().search([('default_code', '=', ref)], limit=1)
            if not tmpl:
                tmpl = self.env['product.template'].sudo().create(template_vals)
                count_products += 1
                _logger.info(f"➕ Producto creado: {ref}")
            else:
                tmpl.sudo().write(template_vals)
                _logger.info(f"🔄 Producto actualizado: {ref}")

            if colors:
                img_url = colors[0].get('packshots', [{}])[0].get('urlPackshot', '')
                if img_url:
                    img_bin = get_image_binary_from_url(img_url)
                    if img_bin:
                        tmpl.sudo().write({'image_1920': img_bin})
                        _logger.info(f"🖼️ Imagen principal asignada a {ref}")

        _logger.info(f"✅ FIN: Asignación de {count_products} productos del catálogo TopTex (con .sudo()).")
        return True

    @api.model
    def sync_stock_from_api(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')

        if not all([api_key, username, password, proxy_url]):
            raise UserError('Faltan parámetros API TopTex')
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_resp.status_code != 200:
            _logger.error(f"❌ Error autenticando para stock: {auth_resp.text}")
            return False
        token = auth_resp.json().get('token', '')
        if not token:
            return False
        headers['x-toptex-authorization'] = token

        stock_url = f'{proxy_url}/v3/products/inventory/result_in_file=1'
        stock_resp = requests.get(stock_url, headers=headers)
        if stock_resp.status_code != 200:
            _logger.error(f"❌ Error obteniendo inventario: {stock_resp.text}")
            return False
        file_link = stock_resp.json().get('link', '')
        if not file_link:
            return False
        json_resp = requests.get(file_link, headers=headers)
        if json_resp.status_code != 200:
            return False
        data = json_resp.json()
        inventory = data if isinstance(data, list) else data.get('items', data)
        count_stock = 0
        for item in inventory:
            sku = item.get('sku', '')
            stock = item.get('inventory', 0)
            if not sku:
                continue
            product = self.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
            if product:
                quants = self.env['stock.quant'].sudo().search([('product_id', '=', product.id), ('location_id.usage', '=', 'internal')])
                if quants:
                    for quant in quants:
                        quant.sudo().inventory_quantity = stock
                        count_stock += 1
                        _logger.info(f"📦 Stock actualizado para {sku}: {stock}")
                else:
                    _logger.warning(f"❌ No hay stock.quant para {sku}")
            else:
                _logger.warning(f"❌ No se encuentra variante para SKU {sku}")
        _logger.info(f"✅ FIN actualización stock ({count_stock}) variantes")

    @api.model
    def sync_variant_images_from_api(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')

        if not all([api_key, username, password, proxy_url]):
            raise UserError('Faltan parámetros API TopTex')
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_payload = {'username': username, 'password': password}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_resp.status_code != 200:
            _logger.error(f"❌ Error autenticando para imágenes: {auth_resp.text}")
            return False
        token = auth_resp.json().get('token', '')
        if not token:
            return False
        headers['x-toptex-authorization'] = token

        catalog_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1'
        cat_resp = requests.get(catalog_url, headers=headers)
        if cat_resp.status_code != 200:
            _logger.error(f"❌ Error obteniendo catálogo para imágenes: {cat_resp.text}")
            return False
        file_link = cat_resp.json().get('link', '')
        if not file_link:
            return False
        json_resp = requests.get(file_link, headers=headers)
        if json_resp.status_code != 200:
            return False
        data = json_resp.json()
        catalog = data if isinstance(data, list) else data.get('items', data)
        count_img = 0

        for prod in catalog:
            colors = prod.get('colors', [])
            for color in colors:
                img_url = color.get('packshots', [{}])[0].get('urlPackshot', '')
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