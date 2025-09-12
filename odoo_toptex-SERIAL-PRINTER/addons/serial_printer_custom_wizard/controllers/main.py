# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SpwCustomizer(http.Controller):

    @http.route(['/spw/customize/<int:product_tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize_page(self, product_tmpl_id, **kwargs):
        """Muestra la página del personalizador.

        Parámetros:
          - product_tmpl_id: id de product.template
          - variant_id (opcional, por querystring): id de product.product seleccionado
        """
        ProductTemplate = request.env['product.template'].sudo()
        ProductProduct = request.env['product.product'].sudo()

        product = ProductTemplate.browse(product_tmpl_id)
        if not product.exists():
            return request.not_found()

        variant = None
        variant_id = kwargs.get('variant_id')
        if variant_id:
            v = ProductProduct.browse(int(variant_id))
            if v.exists() and v.product_tmpl_id.id == product.id:
                variant = v

        # fallback a la variante por defecto si no se pasó una válida
        if not variant:
            variant = product.product_variant_id

        values = {
            'product': product,
            'variant': variant,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)