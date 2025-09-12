# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    @http.route(['/spw/customize/<int:product_tmpl_id>'],
                type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, product_tmpl_id, variant_id=None, **kw):
        # template
        tmpl = request.env['product.template'].sudo().browse(product_tmpl_id).exists()
        if not tmpl:
            return request.not_found()

        variant = None
        if variant_id:
            variant = request.env['product.product'].sudo().browse(int(variant_id)).exists()
            if variant and variant.product_tmpl_id.id != tmpl.id:
                tmpl = variant.product_tmpl_id

        values = {
            'product': tmpl,   # tu template customizer usa 'product'
            'variant': variant,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)