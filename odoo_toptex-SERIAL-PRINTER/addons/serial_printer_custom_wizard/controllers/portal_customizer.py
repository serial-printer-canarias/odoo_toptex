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

        # IMPORTANTÍSIMO: pasar main_object para que el website meta no sea undefined
        values = {
            'product': product,
            'product_tmpl': product,   # alias por si lo usas en templates
            'main_object': product,    # <-- esto evita el TypeError del editor
        }
        return request.render('serial_printer_custom_wizard.website_personalizar_page', values)

    @http.route(['/personalizar/submit'], type='http', auth='public', website=True, csrf=False)
    def personalizar_submit(self, **post):
        # Aquí todavía no hacemos nada con los datos; simplemente volvemos al producto
        pid = int(post.get('product_id', 0))
        return request.redirect(f'/shop/product/{pid}')