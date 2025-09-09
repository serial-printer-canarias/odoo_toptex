# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWPortalCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True, sitemap=False)
    def personalizar(self, product_id, **kw):
        Product = request.env['product.template'].sudo()
        product = Product.browse(product_id)
        if not product.exists():
            return request.not_found()

        # Pasamos explícitamente el objeto principal al contexto
        values = {
            'product': product,
            'main_object': product,              # <- clave para editor
            'main_object_name': 'product.template',
        }
        return request.render('serial_printer_custom_wizard.website_personalizar_page', values)