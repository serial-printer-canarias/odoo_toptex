# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpMatrix(http.Controller):

    @http.route('/sp/matrix/variant_map', type='json', auth='public', website=True, csrf=False)
    def variant_map(self, product_template_id, **kw):
        """Devuelve el mapa de variantes del template:
        [{ 'variant_id': int,
           'ptav_ids': [ids de valores de atributo],
           'image_url': str,
           'stock': float,
           'price': float }]
        """
        tmpl = request.env['product.template'].sudo().browse(int(product_template_id))
        if not tmpl.exists():
            return {"ok": False, "items": []}

        website = request.website
        pricelist = website.get_current_pricelist()

        items = []
        for variant in tmpl.product_variant_ids.sudo():
            ptav_ids = variant.product_template_attribute_value_ids.ids
            # Precio web con lista de precios actual
            # (website_price ya respeta la pricelist en web)
            price = variant.with_context(pricelist=pricelist.id).website_price
            items.append({
                "variant_id": variant.id,
                "ptav_ids": ptav_ids,
                "image_url": f"/web/image/product.product/{variant.id}/image_128",
                "stock": variant.qty_available,
                "price": price,
            })
        return {"ok": True, "items": items}

    @http.route('/sp/matrix/cart/add_multi', type='json', auth='public', website=True, csrf=False)
    def add_multi(self, lines=None, **kw):
        """Añade múltiples líneas al carrito. lines = [{product_id, qty}]"""
        if not lines:
            return {"ok": False, "added": 0}

        # usa el método estándar de website_sale
        cart = request.env['sale.order']._cart_find_or_create_order()
        added = 0
        for l in lines:
            pid = int(l.get('product_id') or 0)
            qty = float(l.get('qty') or 0)
            if pid and qty > 0:
                request.website.sale_get_order()
                request.env['sale.order']._cart_update(product_id=pid, add_qty=qty)
                added += 1
        return {"ok": True, "added": added}