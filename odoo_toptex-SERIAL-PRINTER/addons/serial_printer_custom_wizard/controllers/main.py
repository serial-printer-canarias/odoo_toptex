# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SPWController(http.Controller):

    @http.route(
        '/spw/customize/<int:product_tmpl_id>',
        type='http', auth='public', website=True, csrf=False
    )
    def spw_customize(self, product_tmpl_id, variant_id=None, **kw):
        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        tmpl = ProductTmpl.browse(product_tmpl_id)
        if not tmpl.exists():
            return request.not_found()

        variant = None
        if variant_id:
            try:
                v = Product.browse(int(variant_id))
                if v.exists() and v.product_tmpl_id.id == product_tmpl_id:
                    variant = v
            except Exception:
                variant = None
        if not variant:
            variant = tmpl.product_variant_id

        values = {
            'product_tmpl': tmpl,
            'variant': variant,
        }
        return request.render(
            'serial_printer_custom_wizard.spw_customizer_page', values
        )