import urllib.request
import json
import logging
import base64
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductToptexImport(models.Model):
    _name = 'serial_printer_catalog.models.product'
    _description = 'Importación productos TopTex'

    @api.model
    def importar_toptex_json(self, url_json):
        data = self.descargar_json(url_json)
        items = data.get('items', [])
        if not items:
            return

        for producto in items:
            referencia = producto.get("supplierReference") or producto.get("catalogReference")
            marca = producto.get("brand", "")
            family = producto.get("family", {}).get("es", "")
            description = producto.get("description", {}).get("es", "")
            argumento_venta = producto.get("salesArguments", {}).get("es", "")
            composicion = producto.get("composition", {}).get("es", "")
            imagenes_generales = producto.get("images", [])

            categ = self.env['product.category'].search([('name', '=', family)], limit=1)
            if not categ:
                categ = self.env['product.category'].create({'name': family})

            brand = self.env['product.brand'].search([('name', '=', marca)], limit=1)
            if not brand:
                brand = self.env['product.brand'].create({'name': marca})

            tmpl_vals = {
                'name': referencia,
                'default_code': referencia,
                'categ_id': categ.id,
                'description': description,
                'type': 'product',
                'detailed_type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
                'brand_id': brand.id,
                'description_sale': argumento_venta,
                'standard_price': 0.0,
                'list_price': 0.0,
                'attribute_line_ids': [],
            }

            image_data = False
            if imagenes_generales:
                img_url = imagenes_generales[0].get("url_image", "")
                if img_url:
                    try:
                        image_data = base64.b64encode(urllib.request.urlopen(img_url).read())
                        tmpl_vals['image_1920'] = image_data
                    except:
                        pass

            template = self.env['product.template'].search([('default_code', '=', referencia)], limit=1)
            if not template:
                template = self.env['product.template'].create(tmpl_vals)
            else:
                template.write(tmpl_vals)

            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            talla_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not talla_attr:
                talla_attr = self.env['product.attribute'].create({'name': 'Talla'})

            color_values = []
            talla_values = []

            colores = producto.get("colors", [])
            for color in colores:
                color_nombre = color.get("colors", {}).get("es", "")
                hex_color = color.get("colorsHexa", [""])[0]
                color_value = self.env['product.attribute.value'].search([('name', '=', color_nombre), ('attribute_id', '=', color_attr.id)], limit=1)
                if not color_value:
                    color_value = self.env['product.attribute.value'].create({'name': color_nombre, 'attribute_id': color_attr.id})
                color_values.append(color_value.id)

                for size in color.get("sizes", []):
                    talla = size.get("size", "")
                    talla_value = self.env['product.attribute.value'].search([('name', '=', talla), ('attribute_id', '=', talla_attr.id)], limit=1)
                    if not talla_value:
                        talla_value = self.env['product.attribute.value'].create({'name': talla, 'attribute_id': talla_attr.id})
                    talla_values.append(talla_value.id)

            attr_lines = []
            if color_values:
                attr_lines.append((0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_values)]}))
            if talla_values:
                attr_lines.append((0, 0, {'attribute_id': talla_attr.id, 'value_ids': [(6, 0, talla_values)]}))
            template.attribute_line_ids = [(6, 0, [al[1] for al in attr_lines])]

            for color in colores:
                color_nombre = color.get("colors", {}).get("es", "")
                color_value = self.env['product.attribute.value'].search([('name', '=', color_nombre), ('attribute_id', '=', color_attr.id)], limit=1)
                packshot_face = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")

                for size in color.get("sizes", []):
                    talla = size.get("size", "")
                    talla_value = self.env['product.attribute.value'].search([('name', '=', talla), ('attribute_id', '=', talla_attr.id)], limit=1)
                    ean = size.get("ean", "")
                    sku = size.get("sku", "")
                    price = size.get("prices", [{}])[0].get("price", 0)
                    stock = size.get("unitsPerBox", 0)

                    product = self.env['product.product'].search([
                        ('product_tmpl_id', '=', template.id),
                        ('barcode', '=', ean),
                        ('default_code', '=', sku),
                    ], limit=1)
                    product_vals = {
                        'product_tmpl_id': template.id,
                        'barcode': ean,
                        'default_code': sku,
                        'lst_price': price,
                        'standard_price': price,
                    }
                    if color_value and talla_value:
                        product_vals['attribute_value_ids'] = [(6, 0, [color_value.id, talla_value.id])]

                    if not product:
                        product = self.env['product.product'].create(product_vals)
                    else:
                        product.write(product_vals)

                    if packshot_face:
                        try:
                            image_data = base64.b64encode(urllib.request.urlopen(packshot_face).read())
                            product.image_1920 = image_data
                        except:
                            pass

                    product.qty_available = stock

    @staticmethod
    def descargar_json(url):
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            _logger.error("Error descargando JSON de TopTex: %s", str(e))
            return {}