# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizerPublic(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        Product = request.env['product.product'].sudo()
        Tmpl = request.env['product.template'].sudo()

        tmpl = variant = False
        try:
            if variant_id:
                v = Product.browse(int(variant_id))
                if v.exists():
                    variant = v
                    tmpl = v.product_tmpl_id
            if not tmpl and product_id:
                t = Tmpl.browse(int(product_id))
                if t.exists():
                    tmpl = t
                    if not variant:
                        variant = Product.search([('product_tmpl_id', '=', t.id)], limit=1)
        except Exception:
            pass

        # Construir img_src (siempre una ruta válida)
        img_src = ""
        if variant:
            img_src = "/web/image/product.product/%s/image_1920" % variant.id
        elif tmpl:
            v2 = Product.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
            img_src = "/web/image/product.product/%s/image_1920" % v2.id if v2 else "/web/image/product.template/%s/image_1920" % tmpl.id

        values = {
            "template": tmpl,
            "variant_id": variant.id if variant else False,
            "img_src": img_src,
        }

        # Render seguro de tu vista
        view = request.env.ref('serial_printer_custom_wizard.spw_customize_page', raise_if_not_found=False)
        if view:
            return view._render(values)

        # Fallback: si la vista no existe, no uses website.404 -> redirige
        return request.redirect('/shop')