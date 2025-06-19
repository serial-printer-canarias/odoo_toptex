from odoo import models, fields, api
import requests
import base64

class SerialPrinterProduct(models.Model):
    _inherit = "product.template"

    marca = fields.Char(string='Marca')

    @api.model
    def importar_ns300(self):
        # Configura tus credenciales API
        API_KEY = 'AQUI_TU_API_KEY'
        API_AUTH = 'AQUI_TU_TOKEN_AUTH'
        HEADERS = {
            "x-api-key": API_KEY,
            "x-toptex-authorization": API_AUTH
        }
        REF = "ns300"

        # 1. OBTENCIÓN DATOS GENERALES PRODUCTO
        url_catalog = f"https://toptex-proxy.onrender.com/v3/products/catalog?catalog_reference={REF}"
        r_catalog = requests.get(url_catalog, headers=HEADERS)
        catalog = r_catalog.json()['items'][0]

        # 2. OBTENCIÓN VARIANTES (colores/tallas/foto/sku)
        url_variants = f"https://toptex-proxy.onrender.com/v3/products/catalog/variants?catalog_reference={REF}"
        r_variants = requests.get(url_variants, headers=HEADERS)
        variants = r_variants.json()['items']

        # 3. OBTENCIÓN STOCK POR SKU
        url_stock = f"https://toptex-proxy.onrender.com/v3/products/inventory?catalog_reference={REF}"
        r_stock = requests.get(url_stock, headers=HEADERS)
        stocks = r_stock.json()['items']

        # 4. OBTENCIÓN PRECIOS POR SKU
        url_prices = f"https://toptex-proxy.onrender.com/v3/products/price?catalog_reference={REF}"
        r_prices = requests.get(url_prices, headers=HEADERS)
        prices = r_prices.json()['items']

        # 5. LLAMA A LA CREACIÓN GENERAL (REUTILIZABLE)
        return self.create_product_from_toptex(
            catalog,  # datos generales producto
            variants, # variantes colores/tallas
            prices,   # precios
            stocks    # stocks
        )

    @api.model
    def create_product_from_toptex(self, product_data, variants_data, prices_data, stocks_data):
        brand_name = product_data.get('brand', '')
        # 1. Datos generales producto padre
        vals = {
            'name': product_data.get('designation', ''),
            'default_code': product_data.get('catalogReference', ''),
            'type': 'consu',  # Tipo Odoo, para no romper stock
            'marca': brand_name,
            'description_sale': product_data.get('description', ''),
        }

        # Imagen principal (opcional)
        image_url = product_data.get('mainPicture', '')
        if image_url:
            try:
                img_data = requests.get(image_url).content
                vals['image_1920'] = base64.b64encode(img_data)
            except Exception:
                vals['image_1920'] = False

        # Atributos y variantes
        def get_or_create_attribute(name):
            attr = self.env['product.attribute'].search([('name', '=', name)], limit=1)
            if not attr:
                attr = self.env['product.attribute'].create({'name': name})
            return attr

        color_attr = get_or_create_attribute('Color')
        size_attr = get_or_create_attribute('Talla')

        product_tmpl = self.create(vals)

        # Todos los valores posibles en variantes
        color_values = set()
        size_values = set()
        for v in variants_data:
            color_values.add(v.get('color', ''))
            size_values.add(v.get('size', ''))

        def get_or_create_attr_value(attr, value):
            if not value:
                return False
            val_obj = self.env['product.attribute.value'].search([
                ('name', '=', value),
                ('attribute_id', '=', attr.id)
            ], limit=1)
            if not val_obj:
                val_obj = self.env['product.attribute.value'].create({
                    'name': value,
                    'attribute_id': attr.id
                })
            return val_obj

        color_value_objs = [get_or_create_attr_value(color_attr, c) for c in color_values if c]
        size_value_objs = [get_or_create_attr_value(size_attr, t) for t in size_values if t]

        attribute_lines = []
        if color_value_objs:
            attribute_lines.append((0, 0, {
                'attribute_id': color_attr.id,
                'value_ids': [(6, 0, [cv.id for cv in color_value_objs])]
            }))
        if size_value_objs:
            attribute_lines.append((0, 0, {
                'attribute_id': size_attr.id,
                'value_ids': [(6, 0, [sv.id for sv in size_value_objs])]
            }))
        if attribute_lines:
            product_tmpl.attribute_line_ids = attribute_lines

        product_tmpl._create_variant_ids()

        # Mapea precios y stock por SKU
        price_map = {p['sku']: p for p in prices_data if p.get('sku')}
        stock_map = {s['sku']: s for s in stocks_data if s.get('sku')}
        variant_map = {v['sku']: v for v in variants_data if v.get('sku')}

        # Asigna datos PRO a cada variante
        for variant in product_tmpl.product_variant_ids:
            color_name = ""
            size_name = ""
            for av in variant.attribute_value_ids:
                if av.attribute_id.id == color_attr.id:
                    color_name = av.name
                elif av.attribute_id.id == size_attr.id:
                    size_name = av.name

            # Encuentra el SKU para esta variante (color+size)
            sku = None
            for v in variants_data:
                if v.get('color') == color_name and v.get('size') == size_name:
                    sku = v.get('sku')
                    break
            if not sku:
                continue

            # Precio y coste
            price_info = price_map.get(sku, {})
            cost = float(price_info.get('price', 0.0))
            sale_price = float(price_info.get('sale_price', cost * 1.5))
            # Stock
            stock_info = stock_map.get(sku, {})
            stock = 0
            if stock_info and stock_info.get('warehouses'):
                stock = stock_info['warehouses'][0].get('stock', 0)

            # Imagen de variante
            img_url = variant_map.get(sku, {}).get('picture')
            img_bin = False
            if img_url:
                try:
                    img_bin = base64.b64encode(requests.get(img_url).content)
                except Exception:
                    img_bin = False

            # Asignar datos a la variante
            variant.standard_price = cost
            variant.list_price = sale_price
            variant.qty_available = stock
            if img_bin:
                variant.image_variant_1920 = img_bin

        return product_tmpl