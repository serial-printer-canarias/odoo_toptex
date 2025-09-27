# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    @http.route('/spw/customizer', type='http', auth='public', website=True)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        """Carga la página del personalizador garantizando un variant_id válido."""
        try:
            pid = int(product_id or 0)
        except Exception:
            pid = 0
        if not pid:
            return request.not_found()

        tmpl = request.env['product.template'].sudo().browse(pid)
        if not tmpl or not tmpl.exists():
            return request.not_found()

        # Fallback robusto de variante
        def_variant_id = None
        try:
            def_variant_id = int(variant_id) if variant_id else None
        except Exception:
            def_variant_id = None

        if not def_variant_id:
            # 1) variante "principal" del template
            if tmpl.product_variant_id:
                def_variant_id = tmpl.product_variant_id.id
            # 2) primera variante disponible
            elif tmpl.product_variant_ids:
                def_variant_id = tmpl.product_variant_ids[:1].id

        values = {
            'template': tmpl,
            'variant_id': def_variant_id or 0,
            # Usamos imagen variant same-origin (segura para canvas)
            'img_src': '/web/image/product.product/%s/image_1920' % (def_variant_id or (tmpl.product_variant_id and tmpl.product_variant_id.id) or 0),
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)