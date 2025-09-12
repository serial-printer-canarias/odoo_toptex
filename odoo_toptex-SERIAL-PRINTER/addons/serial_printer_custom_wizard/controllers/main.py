# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SpwCustomizerController(http.Controller):
    """Rutas públicas del personalizador"""

    @http.route(['/spw/customize/<int:tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, tmpl_id, **kwargs):
        """
        Renderiza la página del personalizador para un product.template (tmpl_id).
        Si viene ?variant_id= usa esa variante para la imagen.
        """
        # Producto (template) para el website actual
        ProductTemplate = request.env['product.template'].with_context(
            website_id=request.website.id
        ).sudo()
        template = ProductTemplate.browse(tmpl_id).exists()
        if not template:
            return request.not_found()

        # Variante opcional
        variant = False
        vid = kwargs.get('variant_id')
        try:
            vid = int(vid) if vid else 0
        except Exception:
            vid = 0
        if vid:
            variant = request.env['product.product'].sudo().browse(vid).exists()

        values = {
            'product': template,
            'product_variant': variant or False,
            'variant_id': variant.id if variant else 0,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)