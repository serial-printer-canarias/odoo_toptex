import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            return base64.b64encode(buffer.getvalue())
    except Exception as e:
        _logger.warning(f"Error obteniendo imagen de {url}: {e}")
    return None

def get_price_and_cost(prices, color, size):
    for p in prices:
        if p.get('color') == color and p.get('size') == size:
            plist = p.get('prices', [])
            if plist:
                return plist[0].get('price', 0.0), plist[0].get('price', 0.0)  # Cambia si tienes coste separado
    return 0.0, 0.0

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self, catalog_reference='NS300'):
        # === 1. Token y Headers (tu código)
        url_catalog = f'https://toptex-proxy.onrender.com/v3/products/catalog?catalog_reference={catalog_reference}'
        url_inventory = f'https://toptex-proxy.onrender.com/v3/products/inventory?catalog_reference={catalog_reference}'
        url_prices = f'https://toptex-proxy.onrender.com/v3/products/price?catalog_reference={catalog_reference}'

        headers = {
            'x-api-key': 'AQUÍ_TU_API_KEY',
            'x-toptex-authorization': 'AQUÍ_TU_TOKEN',
        }

        # === 2. Info base de producto (como ya haces)
        r = requests.get(url_catalog, headers=headers)
        catalog = r.json()['items'][0]
        name = catalog.get('designation', '')
        description = catalog.get('description', '')
        default_code = catalog_reference
        image_url = catalog.get('mainPicture')
        image_binary = get_image_binary_from_url(image_url) if image_url else None

        vals = {
            'name': name,
            'default_code': default_code,
            'image_1920': image_binary,
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
            'description': description,
        }
        product = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if product:
            product.write(vals)
        else:
            product = self.create(vals)

        # === 3. Atributos color y talla
        inventory = requests.get(url_inventory, headers=headers).json()['items']
        prices = requests.get(url_prices, headers=headers).json()['items']

        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_map, size_map = {}, {}
        for inv in inventory:
            color = inv.get('color')
            size = inv.get('size')
            if color and color not in color_map:
                val = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': color, 'attribute_id': color_attr.id})
                color_map[color] = val
            if size and size not in size_map:
                val = self.env['product.attribute.value'].search([('name', '=', size), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': size, 'attribute_id': size_attr.id})
                size_map[size] = val

        # Asignar atributos a la plantilla
        product.write({'attribute_line_ids': [(5, 0, 0)]})  # Limpiar líneas
        product.write({'attribute_line_ids': [
            (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_map.values()])] }),
            (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_map.values()])] }),
        ]})

        # === 4. Variantes, imágenes, precios, stock
        for inv in inventory:
            color = inv.get('color')
            size = inv.get('size')
            sku = inv.get('sku')

            # Stock
            stock = 0
            for wh in inv.get('warehouses', []):
                if wh.get('id') == 'toptex':
                    stock = wh.get('stock', 0)

            # Precios
            price, cost = get_price_and_cost(prices, color, size)

            # Imagen variante
            image_variant_url = inv.get('mainPicture') or (inv.get('pictures') or [None])[0] or image_url
            image_variant_binary = get_image_binary_from_url(image_variant_url) if image_variant_url else image_binary

            # Buscar variante, si existe la actualiza, si no la crea
            attribute_ids = [color_map[color].id, size_map[size].id]
            domain = [
                ('product_tmpl_id', '=', product.id),
                ('attribute_value_ids', 'in', color_map[color].id),
                ('attribute_value_ids', 'in', size_map[size].id)
            ]
            variant = self.env['product.product'].search(domain, limit=1)
            variant_vals = {
                'product_tmpl_id': product.id,
                'attribute_value_ids': [(6, 0, attribute_ids)],
                'default_code': sku,
                'image_1920': image_variant_binary,
                'lst_price': price,
                'standard_price': cost,
            }
            if variant:
                variant.write(variant_vals)
            else:
                variant = self.env['product.product'].create(variant_vals)

            # Stock real
            if stock >= 0:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', variant.id),
                    ('location_id', '=', self.env.ref('stock.stock_location_stock').id)
                ], limit=1)
                if quant:
                    quant.write({'quantity': stock})
                else:
                    self.env['stock.quant'].create({
                        'product_id': variant.id,
                        'location_id': self.env.ref('stock.stock_location_stock').id,
                        'quantity': stock,
                    })

        _logger.info(f"✅ Producto {catalog_reference} cargado con variantes, imágenes, precios, stock.")