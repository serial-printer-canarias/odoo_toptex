# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SPWController(http.Controller):

    @http.route(['/spw/customize/<int:variant_id>'], type='http', auth='public', website=True)
    def spw_customize(self, variant_id, **kw):
        """Página de personalización para la variante seleccionada."""
        variant = request.env['product.product'].sudo().browse(variant_id)
        if not variant.exists():
            return request.not_found()

        values = {
            'variant': variant,
            'product_tmpl': variant.product_tmpl_id,
        }
        return request.render('serial_printer_custom_wizard.spw_customizer_page', values)