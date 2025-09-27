# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizer(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, sitemap=False)
    def customizer(self, product_id=None, variant_id=None, **kw):
        """Vista pública del customizer.
        Si no llega variant_id, elegimos una variante del template.
        """
        Product = request.env['product.product'].sudo()
        PTemplate = request.env['product.template'].sudo()

        variant = False
        tmpl = False

        # Resolver template y variante de forma segura
        try:
            if variant_id:
                variant = Product.browse(int(variant_id))
                if variant and variant.exists():
                    tmpl = variant.product_tmpl_id
            if not tmpl and product_id:
                tmpl = PTemplate.browse(int(product_id))
                if tmpl and tmpl.exists() and not variant:
                    # Coger una variante visible
                    variant = Product.search([('product_tmpl_id', '=', tmpl.id)], limit=1)
        except Exception:
            pass

        values = {
            'product_tmpl': tmpl,
            'variant': variant,
        }
        # Renderiza tu plantilla del wizard
        return request.render('serial_printer_custom_wizard.customizer_page', values)