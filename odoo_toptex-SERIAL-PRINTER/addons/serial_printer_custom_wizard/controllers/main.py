# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizer(http.Controller):

    @http.route(['/spw/customize/<int:product_tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, product_tmpl_id, variant_id=None, **kwargs):
        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        product_template = ProductTmpl.browse(product_tmpl_id)
        variant = None
        if variant_id:
            try:
                variant_id = int(variant_id)
                v = Product.browse(variant_id)
                if v.exists() and v.product_tmpl_id.id == product_tmpl_id:
                    variant = v
            except Exception:
                variant = None

        values = {
            "product_template": product_template,
            "product": product_template,          # compat
            "variant": variant,
            "variant_id": variant.id if variant else False,
        }
        return request.render("serial_printer_custom_wizard.spw_customize_page", values)