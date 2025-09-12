# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWController(http.Controller):

    # Acepta /spw/customize y /spw/customize/<tmpl_id>
    @http.route(['/spw/customize', '/spw/customize/<int:tmpl_id>'],
                type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, tmpl_id=None, **kw):
        values = {}
        # Si nos pasan el template, lo mandamos a la vista (no hace falta, pero permite usar product si quieres)
        if tmpl_id:
            product = request.env['product.template'].sudo().browse(tmpl_id)
            if product.exists():
                values['product'] = product
        # Renderiza SIEMPRE la página (no 404)
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)