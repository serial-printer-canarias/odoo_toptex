# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizerPublic(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        Product = request.env['product.product'].sudo()
        PTemplate = request.env['product.template'].sudo()

        variant = tmpl = False
        try:
            if variant_id:
                v = Product.browse(int(variant_id))
                if v.exists():
                    variant = v
                    tmpl = v.product_tmpl_id
            if not tmpl and product_id:
                t = PTemplate.browse(int(product_id))
                if t.exists():
                    tmpl = t
                    if not variant:
                        variant = Product.search([('product_tmpl_id', '=', t.id)], limit=1)
        except Exception:
            pass

        values = {'product_tmpl': tmpl, 'variant': variant}

        # Render robusto por xml_id; si no existe, 404 limpio
        try:
            view = request.env.ref('serial_printer_custom_wizard.customizer_page', raise_if_not_found=True)
            return view._render(values)
        except Exception:
            return request.render('website.404')