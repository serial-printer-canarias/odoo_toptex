# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPMatrixController(http.Controller):

    @http.route('/sp/matrix/combos/<int:template_id>', type='json', auth='public', website=True, csrf=False)
    def sp_matrix_combos(self, template_id, **kw):
        """Devuelve las combinaciones del template con:
           - ptav_ids (ids de product.template.attribute.value)
           - product_id
           - price (con la lista del website)
           - stock (On hand)
           - image (url)
        """
        tmpl = request.env['product.template'].sudo().browse(template_id)
        if not tmpl.exists():
            return {'ok': False, 'error': 'template not found'}

        website   = request.website
        partner   = request.env.user.sudo().partner_id
        pricelist = website.get_current_pricelist()

        items = []
        for p in tmpl.product_variant_ids.sudo():
            # precio con la lista del website (fallback a lst_price)
            price = p.lst_price
            try:
                if hasattr(p, '_get_tax_included_unit_price'):
                    price = p._get_tax_included_unit_price(pricelist, 1.0, partner)
                else:
                    price = p.with_context(
                        pricelist=pricelist.id, partner=partner.id, quantity=1.0
                    ).price or p.lst_price
            except Exception:
                pass

            items.append({
                'product_id': p.id,
                'ptav_ids'  : p.product_template_attribute_value_ids.ids,
                'price'     : price,
                'stock'     : p.qty_available,  # On hand (cámbialo por free_qty si quieres)
                'image'     : f'/web/image/product.product/{p.id}/image_128',
            })
        return {'ok': True, 'items': items}

    @http.route('/sp/cart/add_batch', type='json', auth='public', website=True, csrf=False)
    def sp_cart_add_batch(self, lines=None, **kw):
        """Recibe [{'product_id':id, 'qty':x}, ...] y los añade al carrito."""
        if not isinstance(lines, list):
            return {'ok': False, 'error': 'bad payload'}

        order = request.website.sale_get_order(force_create=True).sudo()
        for ln in lines:
            pid = int(ln.get('product_id') or 0)
            qty = float(ln.get('qty') or 0)
            if pid and qty > 0:
                order._cart_update(product_id=pid, add_qty=qty)
        return {'ok': True, 'order_id': order.id}