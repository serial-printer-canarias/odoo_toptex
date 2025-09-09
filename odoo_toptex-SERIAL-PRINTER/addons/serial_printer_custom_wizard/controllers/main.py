# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SpwPersonalizar(http.Controller):
    # Atendemos dos rutas por si el tema añade /shop/ delante
    @http.route(['/personalizar/<int:product_id>',
                 '/shop/personalizar/<int:product_id>'],
                type='http', auth='public', website=True, sitemap=False)
    def personalizar(self, product_id, **kwargs):
        # Buscamos el template del producto y renderizamos la página
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        values = {'product': product}
        return request.render('serial_printer_custom_wizard.personalizar', values)