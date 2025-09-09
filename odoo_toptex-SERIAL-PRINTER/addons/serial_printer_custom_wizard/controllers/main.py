# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SpwPersonalizar(http.Controller):

    @http.route(
        ['/personalizar/<int:product_id>',
         '/shop/personalizar/<int:product_id>'],
        type='http', auth='public', website=True, sitemap=False
    )
    def personalizar(self, product_id, **kwargs):
        """Página de personalización para un product.template."""
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        # EXPLICAR AL EDITOR DE WEBSITE CUÁL ES EL MAIN OBJECT
        values = {
            'product': product,
            'main_object': product,                 # recordset
            'main_object_name': 'product.template', # nombre del modelo
        }
        return request.render('serial_printer_custom_wizard.personalizar', values)