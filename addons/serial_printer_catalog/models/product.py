import json
import logging
import time
import base64
import requests
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_from_url(url):
    try:
        r = requests.get(url, stream=True, timeout=20)
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
            return base64.b64encode(r.content)
    except Exception as e:
        _logger.warning(f"Error descargando imagen: {url} | {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_toptex_catalog(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')
        if not all([api_key, username, password, proxy_url]):
            raise UserError('Faltan parámetros TopTex en Ajustes > Parámetros del sistema')
        # --- Autenticación ---
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json={'username': username, 'password': password}, headers=headers)
        if auth_resp.status_code != 200:
            raise UserError(f'Error autenticando: {auth_resp.text}')
        token = auth_resp.json().get('token', '')
        if not token:
            raise UserError('No se recibió token TopTex')
        # --- Obtener link del catálogo ALL ---
        all_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1'
        all_headers = {'x-api-key': api_key, 'x-toptex-authorization': token}
        cat_resp = requests.get(all_url, headers=all_headers)
        if cat_resp.status_code != 200:
            raise UserError(f"Error obteniendo catálogo: {cat_resp.text}")
        link = cat_resp.json().get('link')
        if not link:
            raise UserError('No se obtuvo link de catálogo')
        # --- Esperar que el JSON esté generado ---
        productos = []
        for intento in range(20):
            r = requests.get(link)
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data.get('items', data)
                    if isinstance(items, list) and items:
                        productos = items
                        break
                except Exception:
                    pass
            _logger.info(f"Esperando que se genere el JSON ({intento+1}/20)...")
            time.sleep(20)
        if not productos:
            raise UserError("No se pudo descargar catálogo. Espera más tiempo o revisa el link.")
        _logger.info(f"Productos recibidos: {len(productos)}")
        # --- Procesar productos ---
        for prod in productos:
            catalog_ref = prod.get('catalogReference') or prod.get('reference', '')
            name = prod.get('designation', {}).get('es', '') or prod.get('designation', {}).get('en', '') or catalog_ref
            description = prod.get('description', {}).get('es', '') or prod.get('description', {}).get('en', '')
            brand_name = prod.get('brand', '')
            composition = prod.get('composition', {}).get('es', '')
            categ_name = prod.get('family', {}).get('es', '')
            # --- Crear o buscar marca ---
            brand_id = False
            if brand_name:
                Brand = self.env['product.brand'].sudo()
                brand = Brand.search([('name', '=', brand_name)], limit=1)
                if not brand:
                    brand = Brand.create({'name': brand_name})
                brand_id = brand.id
            # --- Crear o buscar categoría ---
            categ_id = self.env['product.category'].sudo().search([('name', '=', categ_name)], limit=1)
            if not categ_id:
                categ_id = self.env.ref('product.product_category_all')
            # --- Colores y Tallas como atributos ---
            color_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].sudo().create({'name': 'Color'})
            size_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Talla')], limit=1)
            if not size_attr:
                size_attr = self.env['product.attribute'].sudo().create({'name': 'Talla'})
            color_vals = set()
            size_vals = set()
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
            vals = {
                'name': f"{brand_name} {name}".strip(),
                'default_code': catalog_ref,
                'description_sale': description,
                'type': 'consu',
                'is_storable': True,
                'brand_id': brand_id,
                'categ_id': categ_id.id,
                'attribute_line_ids': attribute_lines,
                'x_composition': composition,
            }
            template = self.env['product.template'].sudo().search([('default_code', '=', catalog_ref)], limit=1)
            if not template:
                template = self.env['product.template'].sudo().create(vals)
                _logger.info(f"Producto creado: {catalog_ref}")
            else:
                template.sudo().write(vals)
                _logger.info(f"Producto actualizado: {catalog_ref}")
            # --- Imagen principal ---
            images = prod.get('images', [])
            img_url = images[0].get('url_image', '') if images else ''
            if img_url:
                image_bin = get_image_from_url(img_url)
                if image_bin:
                    template.sudo().write({'image_1920': image_bin})
            # --- Mapeo de variantes ---
            for color in prod.get('colors', []):
                color_name = color.get('colors', {}).get('es', '') or color.get('color', '')
                for sz in color.get('sizes', []):
                    size_name = sz.get('size', '')
                    sku = sz.get('sku', '')
                    precio = sz.get('publicUnitPrice', 0)
                    coste = 0
                    precios = sz.get('prices', [])
                    if precios and isinstance(precios, list):
                        coste = precios[0].get('price', 0)
                    ean = sz.get('ean', '')
                    variant = self.env['product.product'].sudo().search([
                        ('product_tmpl_id', '=', template.id),
                        ('product_template_attribute_value_ids.attribute_id', '=', color_attr.id),
                        ('product_template_attribute_value_ids.name', '=', color_name),
                        ('product_template_attribute_value_ids.attribute_id', '=', size_attr.id),
                        ('product_template_attribute_value_ids.name', '=', size_name),
                    ], limit=1)
                    if variant:
                        variant.sudo().write({
                            'default_code': sku,
                            'barcode': ean,
                            'standard_price': float(coste),
                            'lst_price': float(precio),
                        })
        _logger.info("Sincronización TopTex terminada")

    # ----- SERVER ACTION: STOCK -----
    @api.model
    def sync_toptex_stock(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json={'username': username, 'password': password}, headers=headers)
        token = auth_resp.json().get('token', '')
        stock_url = f'{proxy_url}/v3/products/inventory?result_in_file=1'
        all_headers = {'x-api-key': api_key, 'x-toptex-authorization': token}
        cat_resp = requests.get(stock_url, headers=all_headers)
        link = cat_resp.json().get('link')
        stock = []
        for intento in range(20):
            r = requests.get(link)
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data.get('items', data)
                    if isinstance(items, list) and items:
                        stock = items
                        break
                except Exception:
                    pass
            time.sleep(15)
        for item in stock:
            sku = item.get('sku', '')
            inventory = int(item.get('inventory', 0))
            variant = self.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
            if variant:
                quant = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', variant.id),
                    ('location_id.usage', '=', 'internal')
                ], limit=1)
                if quant:
                    quant.sudo().write({'inventory_quantity': inventory})
                    _logger.info(f"Stock actualizado para {sku}: {inventory}")

    # ----- SERVER ACTION: IMÁGENES POR VARIANTE -----
    @api.model
    def sync_toptex_variant_images(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        api_key = IrConfig.get_param('toptex_api_key', '')
        username = IrConfig.get_param('toptex_username', '')
        password = IrConfig.get_param('toptex_password', '')
        proxy_url = IrConfig.get_param('toptex_proxy_url', '')
        headers = {'x-api-key': api_key, 'Content-Type': 'application/json'}
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_resp = requests.post(auth_url, json={'username': username, 'password': password}, headers=headers)
        token = auth_resp.json().get('token', '')
        all_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1'
        all_headers = {'x-api-key': api_key, 'x-toptex-authorization': token}
        cat_resp = requests.get(all_url, headers=all_headers)
        link = cat_resp.json().get('link')
        productos = []
        for intento in range(20):
            r = requests.get(link)
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data.get('items', data)
                    if isinstance(items, list) and items:
                        productos = items
                        break
                except Exception:
                    pass
            time.sleep(15)
        for prod in productos:
            for color in prod.get('colors', []):
                color_name = color.get('colors', {}).get('es', '') or color.get('color', '')
                img_url = ''
                if color.get('packshots', {}).get('FACE'):
                    img_url = color['packshots']['FACE'].get('url_packshot', '')
                if not img_url:
                    continue
                for sz in color.get('sizes', []):
                    sku = sz.get('sku', '')
                    variant = self.env['product.product'].sudo().search([('default_code', '=', sku)], limit=1)
                    if variant and img_url:
                        img_bin = get_image_from_url(img_url)
                        if img_bin:
                            variant.sudo().write({'image_1920': img_bin})
                            _logger.info(f"Imagen asignada a variante {sku}")