# -*- coding: utf-8 -*-
from odoo import models, api, fields
import urllib.request
import json
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_toptex(self, json_url=None):
        # 1. DESCARGA EL JSON DESDE LA URL
        if not json_url:
            json_url = "AQUI_PON_LA_URL_DEL_JSON"  # Cambia por tu URL JSON

        _logger.info("🔗 Descargando catálogo desde %s", json_url)
        try:
            with urllib.request.urlopen(json_url) as response:
                if response.status == 200:
                    json_data_str = response.read().decode('utf-8')
                    data = json.loads(json_data_str)
                else:
                    _logger.error("❌ Error HTTP al descargar JSON: %s", response.status)
                    return
        except Exception as e:
            _logger.error("❌ Error al descargar JSON: %s", e)
            return

        # 2. VALIDA QUE TENGA 'items'
        if 'items' not in data:
            _logger.error("❌ El catálogo descargado no es una lista válida de productos: %s", data)
            return
        items = data['items']

        _logger.info("🟢 Descargados %s productos de Toptex", len(items))

        for item in items:
            # 3. MAPEA INFORMACIÓN DEL PRODUCTO
            default_code = item.get('catalogReference', '')
            name = item.get('designation', {}).get('es') or item.get('designation', {}).get('en', default_code)
            description = item.get('description', {}).get('es', '')
            brand = item.get('brand', '')
            family = item.get('family', {}).get('es', '')
            composition = item.get('composition', {}).get('es', '')
            sales_arguments = item.get('salesArguments', {}).get('es', '')

            # 4. Busca o crea la marca
            brand_id = None
            if brand:
                Brand = self.env['product.brand']
                brand_id = Brand.search([('name', '=', brand)], limit=1)
                if not brand_id:
                    brand_id = Brand.create({'name': brand})
                else:
                    brand_id = brand_id.id

            # 5. Busca o crea el producto principal (plantilla Odoo)
            product_tmpl = self.env['product.template'].search([
                ('default_code', '=', default_code)
            ], limit=1)
            if not product_tmpl:
                product_tmpl = self.env['product.template'].create({
                    'name': name,
                    'default_code': default_code,
                    'type': 'consu',
                    'is_storable': True,
                    'categ_id': self.env.ref('product.product_category_all').id,
                    'description': description,
                    'detailed_type': 'product',
                    'brand_id': brand_id if brand_id else False,
                })
            else:
                product_tmpl.write({
                    'name': name,
                    'description': description,
                    'brand_id': brand_id if brand_id else False,
                })

            # 6. Procesa colores/variantes
            colors = item.get('colors', [])
            for color_data in colors:
                color_name = color_data.get('colors', {}).get('es', '') or color_data.get('colors', {}).get('en', '')
                color_code = color_data.get('sizes', [{}])[0].get('colorCode', '')
                color_hexa = ','.join(color_data.get('colorsHexa', []))
                # Stock, precios, imagenes:
                for size in color_data.get('sizes', []):
                    barcode = size.get('barCode', '')
                    sku = size.get('sku', '')
                    stock = size.get('unitsPerBox', 0)
                    ean = size.get('ean', '')
                    price = 0
                    for p in size.get('prices', []):
                        if p.get('quantity', 0) == 1:
                            price = p.get('price', 0)
                            break
                    public_price = size.get('publicUnitPrice', '')

                    # 7. Busca o crea variante/product.product
                    product_variant = self.env['product.product'].search([
                        ('default_code', '=', sku)
                    ], limit=1)
                    vals = {
                        'product_tmpl_id': product_tmpl.id,
                        'default_code': sku,
                        'barcode': barcode or ean,
                        'lst_price': public_price.replace("â¬", "").replace(",", ".").strip() if isinstance(public_price, str) else public_price,
                        'standard_price': price,
                        'attribute_value_ids': [],
                    }
                    if not product_variant:
                        product_variant = self.env['product.product'].create(vals)
                    else:
                        product_variant.write(vals)

                    # 8. Asigna stock (puedes usar tu propio método si usas stock.multi o stock.quant)
                    # Aquí solo muestra en el log
                    _logger.info(f"VARIANTE {sku} COLOR {color_name}: STOCK {stock}, PRECIO COSTE {price}, PUBLICO {public_price}")

                    # 9. Imágenes por variante/color
                    packshots = color_data.get('packshots', {})
                    urls_imgs = []
                    if packshots:
                        for k in packshots:
                            if 'url_packshot' in packshots[k]:
                                urls_imgs.append(packshots[k]['url_packshot'])
                    # Asigna la imagen a la variante (si usas web.image, implementa el método correspondiente)
                    if urls_imgs:
                        img_url = urls_imgs[0]
                        try:
                            import base64
                            with urllib.request.urlopen(img_url) as response:
                                img = base64.b64encode(response.read())
                                product_variant.image_1920 = img
                        except Exception as e:
                            _logger.warning(f"No se pudo descargar imagen {img_url}: {e}")

            # Puedes agregar aquí más mapeos de atributos, composiciones, familia, etc.

        _logger.info("✅ Sincronización de catálogo Toptex finalizada.")
        return True