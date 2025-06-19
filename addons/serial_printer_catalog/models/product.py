import json
import logging
import requests
import base64
import io
from PIL import Image
from odoo import models, api, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def get_image_binary_from_url(url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG")
            image_bytes = buffer.getvalue()
            return base64.b64encode(image_bytes)
        else:
            _logger.warning(f"⚠️ Imagen no encontrada: {url}")
    except Exception as e:
        _logger.warning(f"❌ Error imagen {url}: {e}")
    return None

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self, catalog_reference='NS300'):
        # Configura aquí tus endpoints y claves reales
        api_url_catalog = f"https://toptex-proxy.onrender.com/v3/products/catalog?reference={catalog_reference}"
        api_url_inventory = f"https://toptex-proxy.onrender.com/v3/products/inventory?catalog_reference={catalog_reference}"
        api_url_prices = f"https://toptex-proxy.onrender.com/v3/products/price?catalog_reference={catalog_reference}"

        headers = {
            'x-api-key': 'TU_API_KEY',
            'x-toptex-authorization': 'TU_AUTH'
        }

        # --- INFO BASE PRODUCTO ---
        response_catalog = requests.get(api_url_catalog, headers=headers)
        if response_catalog.status_code != 200:
            raise UserError('Error obteniendo datos base del producto')
        catalog_data = response_catalog.json()['items'][0]
        name = catalog_data.get('designation', 'Producto sin nombre')
        description = catalog_data.get('description', '')
        default_code = catalog_reference

        # Imagen principal del producto
        image_url = catalog_data.get('mainPicture') or (catalog_data.get('pictures') or [None])[0]
        image_binary = get_image_binary_from_url(image_url) if image_url else None

        # --- CREAR O ACTUALIZAR PLANTILLA ---
        vals = {
            'name': name,
            'default_code': default_code,
            'image_1920': image_binary,
            'type': 'consu',  # Consumible
            'sale_ok': True,
            'purchase_ok': True,
            'description': description,
        }
        product = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if product:
            product.write(vals)
        else:
            product = self.create(vals)

        # --- ATRIBUTOS Y VALORES (Color y Talla) ---
        # Buscar o crear atributos
        attr_obj = self.env['product.attribute']
        val_obj = self.env['product.attribute.value']

        # Nos aseguramos que los atributos existan
        attr_color = attr_obj.search([('name', '=', 'Color')], limit=1)
        if not attr_color:
            attr_color = attr_obj.create({'name': 'Color'})
        attr_size = attr_obj.search([('name', '=', 'Talla')], limit=1)
        if not attr_size:
            attr_size = attr_obj.create({'name': 'Talla'})

        # --- STOCK Y VARIANTES ---
        response_inventory = requests.get(api_url_inventory, headers=headers)
        inventory_data = response_inventory.json()['items'] if response_inventory.status_code == 200 else []

        # --- PRECIOS ---
        response_prices = requests.get(api_url_prices, headers=headers)
        prices_data = response_prices.json()['items'] if response_prices.status_code == 200 else []

        # --- CREAR VALORES DE ATRIBUTO Y MAPEO ---
        color_map = {}
        size_map = {}

        for v in inventory_data:
            color = v.get('color')
            size = v.get('size')
            # Crear valores de color
            if color and color not in color_map:
                color_val = val_obj.search([('name', '=', color), ('attribute_id', '=', attr_color.id)], limit=1)
                if not color_val:
                    color_val = val_obj.create({'name': color, 'attribute_id': attr_color.id})
                color_map[color] = color_val
            # Crear valores de talla
            if size and size not in size_map:
                size_val = val_obj.search([('name', '=', size), ('attribute_id', '=', attr_size.id)], limit=1)
                if not size_val:
                    size_val = val_obj.create({'name': size, 'attribute_id': attr_size.id})
                size_map[size] = size_val

        # Asignar atributos al producto
        product.attribute_line_ids = [(5, 0, 0)]  # Limpiar líneas anteriores
        product.attribute_line_ids = [
            (0, 0, {'attribute_id': attr_color.id, 'value_ids': [(6, 0, [val.id for val in color_map.values()])]}),
            (0, 0, {'attribute_id': attr_size.id, 'value_ids': [(6, 0, [val.id for val in size_map.values()])]}),
        ]

        # --- CREAR VARIANTES ---
        # Borra variantes antiguas si hay (opcional)
        for variant in product.product_variant_ids:
            variant.unlink()

        for inv in inventory_data:
            color = inv.get('color')
            size = inv.get('size')
            sku = inv.get('sku')
            # Stock
            stock = 0
            for wh in inv.get('warehouses', []):
                if wh.get('id') == 'toptex':
                    stock = wh.get('stock', 0)
            # Precio de compra/venta
            price = 0.0
            cost = 0.0
            for p in prices_data:
                if p.get('color') == color and p.get('size') == size:
                    prices = p.get('prices', [])
                    if prices:
                        price = prices[0].get('price', 0.0)
                        cost = price  # Si tienes coste separado, cámbialo aquí

            # Imagen de variante
            image_variant_url = None
            if 'pictures' in inv and inv['pictures']:
                image_variant_url = inv['pictures'][0]
            elif 'mainPicture' in inv:
                image_variant_url = inv['mainPicture']
            else:
                image_variant_url = image_url
            image_variant_binary = get_image_binary_from_url(image_variant_url) if image_variant_url else image_binary

            # Crea la variante en Odoo
            variant_vals = {
                'product_tmpl_id': product.id,
                'attribute_value_ids': [(6, 0, filter(None, [color_map.get(color).id, size_map.get(size).id]))],
                'default_code': sku,
                'image_1920': image_variant_binary,
                'lst_price': price,
                'standard_price': cost,
                'quantity': stock,
            }
            self.env['product.product'].create(variant_vals)

        _logger.info(f"✅ Producto {catalog_reference} creado/sincronizado con todas las variantes (color, talla), imágenes, precios y stock.")