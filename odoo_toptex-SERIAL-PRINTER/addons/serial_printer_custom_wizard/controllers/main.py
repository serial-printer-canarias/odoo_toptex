# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizeController(http.Controller):

    @http.route(['/spw/customize/<int:product_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, product_id, variant_id=None, **kw):
        """Muestra la página de personalización.
        product_id: ID de product.template
        variant_id (opcional): ID de product.product seleccionado en la ficha.
        """
        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        product = ProductTmpl.browse(product_id).exists()
        if not product:
            return request.not_found()

        variant = None
        if variant_id:
            try:
                variant = Product.browse(int(variant_id)).exists()
            except Exception:
                variant = None
            # Por seguridad, que pertenezca a la plantilla
            if not variant or variant.product_tmpl_id.id != product.id:
                variant = None

        if not variant:
            # Variante por defecto de la plantilla
            variant = product.product_variant_id

        values = {
            'product': product,
            'variant': variant,
        }
        # Renderiza la vista QWeb del customizador
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)