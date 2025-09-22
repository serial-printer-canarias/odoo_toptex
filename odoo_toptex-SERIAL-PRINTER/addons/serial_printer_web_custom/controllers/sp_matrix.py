# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpMatrix(http.Controller):

    @http.route('/sp/matrix/combos/<int:template_id>', type='json', auth='public', csrf=False, website=True)
    def sp_matrix_combos(self, template_id, **kw):
        template = request.env['product.template'].sudo().browse(template_id)
        if not template.exists():
            return {"ok": False, "items": []}

        items = []
        for v in template.product_variant_ids.sudo():
            ptav_ids = v.product_template_attribute_value_ids.ids
            pav_ids = v.product_template_attribute_value_ids.mapped('product_attribute_value_id').ids
            price = float(getattr(v, 'website_price', v.lst_price) or 0.0)
            stock = float(getattr(v, 'qty_available', 0.0) or 0.0)
            image_url = f"/web/image/product.product/{v.id}/image_128"
            items.append({
                "product_id": v.id,
                "ptav_ids": ptav_ids,
                "pav_ids": pav_ids,
                "price": price,
                "stock": stock,
                "image": image_url,
            })
        return {"ok": True, "items": items}

    @http.route('/sp/cart/add_batch', type='json', auth='public', csrf=False, website=True)
    def sp_cart_add_batch(self, lines=None, **kw):
        lines = lines or []
        order = request.website.sale_get_order(force_create=1)
        for l in lines:
            pid = int(l.get("product_id", 0))
            qty = float(l.get("qty", 0))
            if pid and qty > 0:
                order._cart_update(product_id=pid, add_qty=qty)
        return {"ok": True, "line_count": len(lines)}