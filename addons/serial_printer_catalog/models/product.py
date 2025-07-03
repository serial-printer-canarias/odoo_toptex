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
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            return base64.b64encode(response.content)
        else:
            _logger.warning(f"⚠️ Imagen no válida: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error descargando imagen: {url} -> {e}")
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
        _logger.info(f"🟢 AUTH TopTex: {auth_url}")
        auth_resp = requests.post(auth_url, json=auth_payload, headers=headers)
        if auth_resp.status_code != 200:
            raise UserError(f"Error autenticando: {auth_resp.text}")
        token = auth_resp.json().get('token', '')
        if not token:
            raise UserError('No se recibió token TopTex')
        headers['x-toptex-authorization'] = token

        catalog_url = f'{proxy_url}/v3/products/all?usage_right=b2b_b2c&display_prices=1&result_in_file=1'
        _logger.info(f"🟢 CATALOG URL: {catalog_url}")
        cat_resp = requests.get(catalog_url, headers=headers)
        if cat_resp.status_code != 200:
            raise UserError(f"Error obteniendo catálogo: {cat_resp.text}")
        file_link = cat_resp.json().get('link', '')
        _logger.info(f"Link temporal: {file_link}")
        if not file_link:
            raise UserError('No se obtuvo el link del JSON de productos')
        json_resp = requests.get(file_link, headers=headers)
        if json_resp.status_code != 200:
            raise UserError(f"Error descargando el JSON catálogo: {json_resp.text}")
        try:
            data = json_resp.json()
        except Exception as e:
            _logger.error(f"Error parseando JSON: {e}")
            return

        catalog = data if isinstance(data, list) else data.get('items', data)
        _logger.info(f"Productos recibidos: {len(catalog) if isinstance(catalog, list) else 'no-list'}")
        if not catalog or (isinstance(catalog, list) and len(catalog) == 0):
            _logger.error("Catálogo vacío")
            return

        count_products = 0
        brands_cache = {}
        # Preparar atributos (solo 1 vez)
        color_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].sudo().create({'name': 'Color'})
        size_attr = self.env['product.attribute'].sudo().search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].sudo().create({'name': 'Talla'})

        for prod in catalog:
            # DATOS BÁSICOS
            default_code = prod.get('catalogReference', '') or prod.get('reference', '')
            brand_name = prod.get('brand', '')
            if isinstance(brand_name, dict):
                brand_name = brand_name.get('name', '') or brand_name.get('es', '') or ''
            name = prod.get('designation', {}).get('es', '') or prod.get('designation', {}).get('en', '')
            description = prod.get('description', {}).get('es', '') or prod.get('description', {}).get('en', '')

            # MARCA
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

            # CATEGORÍA
            cat_name = prod.get('category', '')
            categ_obj = self.env['product.category'].sudo().search([('name', '=', cat_name)], limit=1) if cat_name else False
            if not categ_obj:
                categ_obj = self.env['product.category'].sudo().search([('name', '=', 'All')], limit=1)
                if not categ_obj:
                    categ_obj = self.env['product.category'].sudo().create({'name': 'All'})

            # ATRIBUTOS Color/Talla (preparar valores)
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

            # CREAR/ACTUALIZAR PRODUCTO
            template_vals = {
                'name': f"{brand_name} {name}",
                'default_code': default_code,
                'description_sale': description,
                'type': 'consu',
                'is_storable': True,
                'categ_id': categ_obj.id if categ_obj else False,
                'brand_id': brand_obj.id if brand_obj else False,
                'attribute_line_ids': attribute_lines,
            }

            tmpl = self.env['product.template'].sudo().search([('default_code', '=', default_code)], limit=1)
            if not tmpl:
                tmpl = self.env['product.template'].sudo().create(template_vals)
                count_products += 1
                _logger.info(f"➕ Producto creado: {default_code}")
            else:
                tmpl.sudo().write(template_vals)
                _logger.info(f"🔄 Producto actualizado: {default_code}")

            # VARIANTES (actualizar datos clave y EAN)
            for color in prod.get('colors', []):
                color_name = color.get('colors', {}).get('es', '') or color.get('color', '')
                img_url = None
                packshots = color.get('packshots', {})
                if "FACE" in packshots:
                    img_url = packshots["FACE"].get("url_packshot", "")
                for sz in color.get('sizes', []):
                    size_name = sz.get('size', '')
                    sku = sz.get('sku', '')
                    precio_coste = sz.get('publicUnitPrice', 0.0)
                    ean = sz.get('ean', '')
                    # Buscar variante por SKU (o combinación)
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
                        # Imagen variante
                        if img_url:
                            img_bin = get_image_binary_from_url(img_url)
                            if img_bin:
                                variant.sudo().write({'image_1920': img_bin})
                                _logger.info(f"🖼️ Imagen asignada a SKU: {sku}")
                    else:
                        _logger.warning(f"❌ Variante no encontrada para SKU: {sku}")

            # IMAGEN PRINCIPAL
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

        _logger.info(f"✅ FIN: Asignación de {count_products} productos (PRO) TopTex (con .sudo()).")
        return True