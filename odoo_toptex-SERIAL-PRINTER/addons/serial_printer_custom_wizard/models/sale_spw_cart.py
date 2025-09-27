# -*- coding: utf-8 -*-
import uuid
from odoo import http
from odoo.http import request

class SPWCartController(http.Controller):

    @http.route(['/spw/add_to_cart'], type='json', auth='public', website=True, csrf=False)
    def spw_add_to_cart(self, product_id, quantity=1, **kw):
        # token único por personalización
        spw_token = kw.get('spw_token') or uuid.uuid4().hex[:12]

        order = request.website.sale_get_order(force_create=True)
        res = order._cart_update(
            product_id=int(product_id),
            add_qty=float(quantity),
            # ¡sin line_id para no forzar update de una línea existente!
            spw_token=spw_token,
        )

        # Respondemos con el token y la line_id creada (útil para previews)
        res['spw_token'] = spw_token
        return res