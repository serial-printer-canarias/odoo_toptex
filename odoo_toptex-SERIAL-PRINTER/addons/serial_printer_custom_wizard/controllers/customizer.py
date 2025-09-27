# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizerPage(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        """Renderiza la página del customizer con imagen same-origin."""
        product_t = request.env['product.template'].sudo().browse(int(product_id or 0))
        vid = int(variant_id or (product_t.product_variant_id.id if product_t and product_t.product_variant_id else 0) or 0)
        if vid:
            img_src = f'/web/image/product.product/{vid}/image_1920'
        else:
            img_src = f'/web/image/product.template/{product_t.id}/image_1920' if product_t else ''
        values = {
            'template': product_t,
            'variant_id': vid,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)