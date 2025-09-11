# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWController(http.Controller):

    @http.route(['/personalizar/<int:pid>'], type='http', auth='public', website=True, sitemap=False)
    def personalizar(self, pid, **kw):
        """pid puede ser product.product (variante) o product.template."""
        Product = request.env['product.product'].sudo()
        Variant = Product.browse(pid)
        if Variant.exists():
            product_variant = Variant
            product_tmpl = Variant.product_tmpl_id
        else:
            product_tmpl = request.env['product.template'].sudo().browse(pid)
            product_variant = product_tmpl.product_variant_id

        values = {
            'product_tmpl': product_tmpl,
            'product_variant': product_variant,
            'product_name': f"[{product_tmpl.default_code or ''}] {product_tmpl.name}",
        }
        return request.render('serial_printer_custom_wizard.spw_customizer_page', values)