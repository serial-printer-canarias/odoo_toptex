# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    # URL: /spw/customize/<product.template.id>?variant_id=<product.product.id>
    @http.route(['/spw/customize/<int:tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, tmpl_id, variant_id=None, **kw):
        ProductTemplate = request.env['product.template'].sudo()
        ProductProduct  = request.env['product.product'].sudo()

        template = ProductTemplate.browse(tmpl_id).exists()
        if not template:
            return request.not_found()

        variant = None
        # Si viene variant_id lo validamos que pertenezca al template
        if variant_id:
            v = ProductProduct.browse(int(variant_id)).exists()
            if v and v.product_tmpl_id.id == tmpl_id:
                variant = v

        # Fallback variante por defecto del template (NO cambiamos de producto)
        if not variant:
            variant = template.product_variant_id

        # Imagen de la variante si existe, si no la del template
        if variant:
            img_src = f"/web/image/product.product/{variant.id}/image_1920"
        else:
            img_src = f"/web/image/product.template/{template.id}/image_1920"

        values = {
            'template': template,
            'variant': variant,
            'img_src': img_src,
        }
        # Importante: este ID debe coincidir con tu vista XML de la página
        return request.render('serial_printer_custom_wizard.customizer_page', values)