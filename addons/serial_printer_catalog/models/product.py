import requests
import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def toptex_generate_token(self):
        auth_url = self.env['ir.config_parameter'].sudo().get_param('toptex_auth_url')
        client_id = self.env['ir.config_parameter'].sudo().get_param('toptex_client_id')
        client_secret = self.env['ir.config_parameter'].sudo().get_param('toptex_client_secret')
        proxy = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy')
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        proxies = {'https': proxy} if proxy else None
        response = requests.post(auth_url, data=data, proxies=proxies, timeout=60)
        if response.status_code == 200:
            token = response.json()['access_token']
            self.env['ir.config_parameter'].sudo().set_param('toptex_api_token', token)
            return token
        else:
            raise UserError(_('Token error: %s') % response.text)

    @api.model
    def sync_toptex_catalog(self):
        api_url = self.env['ir.config_parameter'].sudo().get_param('toptex_api_url')
        usage_right = self.env['ir.config_parameter'].sudo().get_param('toptex_usage_right', 'b2b_b2c')
        page_size = int(self.env['ir.config_parameter'].sudo().get_param('toptex_page_size', default='50'))
        lang = self.env['ir.config_parameter'].sudo().get_param('toptex_lang', 'es')
        proxy = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex_api_token') or self.toptex_generate_token()
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        proxies = {'https': proxy} if proxy else None
        page = 1
        total_created = 0
        while True:
            params = {
                "usage_right": usage_right,
                "page_number": page,
                "page_size": page_size,
                "lang": lang
            }
            _logger.info(f"Llamando a TopTex página {page}")
            response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=300)
            if response.status_code == 401:
                token = self.toptex_generate_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=300)
            if response.status_code != 200:
                raise UserError(_('Error TopTex API: %s') % response.text)
            data = response.json()
            items = data.get('items', [])
            if not items:
                break
            for item in items:
                self.create_or_update_from_toptex(item)
                total_created += 1
            if len(items) < page_size:
                break
            page += 1
        _logger.info(f"Catálogo TopTex sincronizado: {total_created} productos.")
        return {'type': 'ir.actions.act_window_close'}

    def create_or_update_from_toptex(self, item):
        sku = item.get('catalogReference') or item.get('sku') or ''
        name = item.get('designation') or item.get('name') or sku
        brand_name = item.get('brand', '') or ''
        description = item.get('description', '')
        price = item.get('prices', {}).get('public', 0.0)
        cost = item.get('prices', {}).get('cost', 0.0)
        image_url = ''
        if item.get('images'):
            cover_images = [img['url'] for img in item['images'] if img.get('cover')]
            image_url = cover_images[0] if cover_images else item['images'][0].get('url', '')
        color_list = []
        size_list = []
        if 'colors' in item and isinstance(item['colors'], list):
            color_list = [c.get('name', '') if isinstance(c, dict) else c for c in item['colors']]
        if 'sizes' in item and isinstance(item['sizes'], list):
            size_list = [s.get('name', '') if isinstance(s, dict) else s for s in item['sizes']]
        brand_id = False
        if brand_name:
            Brand = self.env['product.brand']
            brand_id = Brand.search([('name', '=', brand_name)], limit=1)
            if not brand_id:
                brand_id = Brand.create({'name': brand_name})
        Product = self.env['product.template']
        product = Product.search([('default_code', '=', sku)], limit=1)
        if not product:
            product = Product.create({
                'name': name,
                'default_code': sku,
                'description': description,
                'list_price': price,
                'standard_price': cost,
                'brand_id': brand_id.id if brand_id else False,
            })
        else:
            product.write({
                'name': name,
                'description': description,
                'list_price': price,
                'standard_price': cost,
                'brand_id': brand_id.id if brand_id else False,
            })
        if image_url:
            try:
                img_data = requests.get(image_url, timeout=30).content
                product.image_1920 = img_data
            except Exception as e:
                _logger.error(f"Error descargando imagen {image_url}: {e}")
        attr_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not attr_color and color_list:
            attr_color = self.env['product.attribute'].create({'name': 'Color'})
        attr_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not attr_size and size_list:
            attr_size = self.env['product.attribute'].create({'name': 'Talla'})
        color_vals = []
        size_vals = []
        for color in color_list:
            val = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', attr_color.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': color, 'attribute_id': attr_color.id})
            color_vals.append(val.id)
        for size in size_list:
            val = self.env['product.attribute.value'].search([('name', '=', size), ('attribute_id', '=', attr_size.id)], limit=1)
            if not val:
                val = self.env['product.attribute.value'].create({'name': size, 'attribute_id': attr_size.id})
            size_vals.append(val.id)
        attr_lines = []
        if attr_color and color_vals:
            attr_lines.append((0, 0, {'attribute_id': attr_color.id, 'value_ids': [(6, 0, color_vals)]}))
        if attr_size and size_vals:
            attr_lines.append((0, 0, {'attribute_id': attr_size.id, 'value_ids': [(6, 0, size_vals)]}))
        if attr_lines:
            product.attribute_line_ids = attr_lines

    # --- Server Action para STOCK ---
    @api.model
    def sync_toptex_stock(self):
        api_url = self.env['ir.config_parameter'].sudo().get_param('toptex_stock_url')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex_api_token') or self.toptex_generate_token()
        proxy = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy')
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        proxies = {'https': proxy} if proxy else None

        # Ejemplo: Recorrer todos los productos
        products = self.env['product.template'].search([('default_code', '!=', False)])
        for product in products:
            sku = product.default_code
            params = {'reference': sku}
            response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=60)
            if response.status_code == 401:
                token = self.toptex_generate_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=60)
            if response.status_code != 200:
                _logger.error(f"Error stock {sku}: {response.text}")
                continue
            stock_data = response.json()
            # Ajusta el campo según la estructura real del endpoint de stock TopTex
            qty = stock_data.get('quantity', 0)
            product.qty_available = qty  # O el campo correspondiente
            # Si tienes variantes, aquí puedes iterar variantes también

    # --- Server Action para IMÁGENES POR VARIANTE ---
    @api.model
    def sync_toptex_images(self):
        api_url = self.env['ir.config_parameter'].sudo().get_param('toptex_image_url')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex_api_token') or self.toptex_generate_token()
        proxy = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy')
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        proxies = {'https': proxy} if proxy else None

        products = self.env['product.template'].search([('default_code', '!=', False)])
        for product in products:
            sku = product.default_code
            params = {'reference': sku}
            response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=60)
            if response.status_code == 401:
                token = self.toptex_generate_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(api_url, headers=headers, params=params, proxies=proxies, timeout=60)
            if response.status_code != 200:
                _logger.error(f"Error imágenes {sku}: {response.text}")
                continue
            images_data = response.json()
            # Ajusta a la estructura real del endpoint de imágenes por variante
            if 'variants' in images_data:
                for v in images_data['variants']:
                    color = v.get('color')
                    size = v.get('size')
                    image_url = v.get('image_url')
                    variant = self.env['product.product'].search([
                        ('product_tmpl_id', '=', product.id),
                        ('attribute_value_ids.name', '=', color),
                        ('attribute_value_ids.name', '=', size)
                    ], limit=1)
                    if variant and image_url:
                        try:
                            img_data = requests.get(image_url, timeout=30).content
                            variant.image_variant_1920 = img_data
                        except Exception as e:
                            _logger.error(f"Error imagen variante {sku}-{color}-{size}: {e}")