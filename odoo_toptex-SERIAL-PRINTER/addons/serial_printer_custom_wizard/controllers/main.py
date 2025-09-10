# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwWebsite(http.Controller):
    @http.route(['/spw/personalizar/<int:tmpl_id>'], type='http', auth="public", website=True, sitemap=False)
    def spw_personalizar(self, tmpl_id, **kwargs):
        product = request.env['product.template'].sudo().browse(tmpl_id)
        if not product.exists():
            return request.not_found()
        return request.render('serial_printer_custom_wizard.website_personalizar_page', {
            'product': product,
            'return_url': product.website_url or '/shop',
        })