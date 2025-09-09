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

        # Pasamos el objeto principal para el editor del Website
        values = {
            'product': product,
            'product_tmpl': product,
            'main_object': product,  # <-- clave para evitar el TypeError
        }
        return request.render('serial_printer_custom_wizard.website_personalizar_page', values)

    @http.route(['/personalizar/submit'], type='http', auth='public', website=True, csrf=False)
    def personalizar_submit(self, **post):
        pid = int(post.get('product_id', 0))
        return request.redirect(f'/shop/product/{pid}')