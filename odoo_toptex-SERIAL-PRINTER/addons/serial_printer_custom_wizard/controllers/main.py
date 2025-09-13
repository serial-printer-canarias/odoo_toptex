# addons/serial_printer_custom_wizard/controllers/main.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizerController(http.Controller):

    @http.route(['/spw/customize/<int:template_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id, **kw):
        """Renderiza la página del personalizador.
        Usa la variante pasada en ?variant_id=<product.product.id> si existe y es del template.
        Si no, cae a la imagen del template.
        """
        Website = request.env['website'].sudo()
        template = request.env['product.template'].sudo().browse(template_id).exists()
        if not template:
            return request.not_found()

        # Param opcional con la variante seleccionada (product.product id)
        variant_id = kw.get('variant_id')
        variant = None
        if variant_id:
            try:
                variant_id = int(variant_id)
            except Exception:
                variant_id = None

        if variant_id:
            variant = request.env['product.product'].sudo().browse(variant_id).exists()
            # Seguridad: la variante debe pertenecer al template solicitado
            if not variant or variant.product_tmpl_id.id != template.id:
                variant = None

        # Construir URL de imagen (prioridad: variante -> template)
        if variant:
            img_src = f"/web/image/product.product/{variant.id}/image_1024"
        else:
            img_src = f"/web/image/product.template/{template.id}/image_1024"

        values = {
            'website': Website.get_current_website(),
            'template': template,
            'variant': variant,
            'variant_id': variant.id if variant else None,
            'img_src': img_src,
            # Para editor de Website: evita error 'mainObject.model'
            'pageName': 'spw_customize_page',
            'main_object': template,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)