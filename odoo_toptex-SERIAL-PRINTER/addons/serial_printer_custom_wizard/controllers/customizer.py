# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizer(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, methods=['GET'])
    def spw_customizer(self, **kw):
        """Página del personalizador /spw/customizer?product_id=XX&variant_id=YY"""
        pid = int(kw.get('product_id') or 0)
        vid = int(kw.get('variant_id') or 0)

        ProductT = request.env['product.template'].sudo()
        ProductV = request.env['product.product'].sudo()

        template = ProductT.browse(pid) if pid else None
        variant = ProductV.browse(vid) if vid else None

        if not template and variant:
            template = variant.product_tmpl_id

        # Fallbacks seguros
        if not variant and template:
            variant = template.product_variant_id

        # Imagen visible (no se usa para el canvas, solo para UI)
        img_src = ''
        if variant and variant.id:
            img_src = '/web/image/product.product/%s/image_1920' % variant.id
        elif template and template.id:
            img_src = '/web/image/product.template/%s/image_1920' % template.id

        values = {
            'template': template,
            'variant_id': variant.id if variant else 0,
            'img_src': img_src,
        }
        # IMPORTANTE: request.render (no _render)
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)