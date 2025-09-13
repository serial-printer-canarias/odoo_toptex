# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizerController(http.Controller):

    @http.route(['/spw/customize/<int:template_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id, **kw):
        """
        Renderiza el personalizador mostrando la imagen CORRECTA:
        - Si llega ?variant_id= o ?product_id= (id de product.product), usamos esa variante
        - Si no, usamos la imagen del template
        """
        template = request.env['product.template'].sudo().browse(template_id).exists()
        if not template:
            return request.not_found()

        # Aceptar variant_id o product_id (ambos son product.product.id)
        raw_variant = kw.get('variant_id') or kw.get('product_id')
        variant = None
        if raw_variant:
            try:
                pp_id = int(raw_variant)
                v = request.env['product.product'].sudo().browse(pp_id).exists()
                if v and v.product_tmpl_id.id == template.id:
                    variant = v
            except Exception:
                variant = None

        if variant:
            img_src = f"/web/image/product.product/{variant.id}/image_1024"
        else:
            img_src = f"/web/image/product.template/{template.id}/image_1024"

        values = {
            'template': template,
            'variant': variant,
            'variant_id': variant.id if variant else None,
            'img_src': img_src,
            # Evita errores del editor de Website
            'pageName': 'spw_customize_page',
            'main_object': template,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)