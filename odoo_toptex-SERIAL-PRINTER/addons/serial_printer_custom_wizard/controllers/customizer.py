# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPWCustomizer(http.Controller):

    @http.route('/spw/customizer', type='http', auth='public', website=True)
    def spw_customizer(self, product_id=None, product_template_id=None, variant_id=None, **kw):
        """Renderiza la página del personalizador."""
        env = request.env
        Product = env['product.product'].sudo()
        Template = env['product.template'].sudo()

        variant = None
        template = None

        if variant_id:
            variant = Product.browse(int(variant_id))
            if variant and variant.exists():
                template = variant.product_tmpl_id
        elif product_id:
            # por compatibilidad, product_id también puede ser la variante
            v = Product.browse(int(product_id))
            if v and v.exists():
                variant = v
                template = v.product_tmpl_id
        elif product_template_id:
            template = Template.browse(int(product_template_id))

        if not template:
            return request.not_found()

        if not variant:
            variant = template.product_variant_id

        # Imagen base mostrada en la página
        img_src = variant and f"/web/image/product.product/{variant.id}/image_1920" or f"/web/image/product.template/{template.id}/image_1920"

        values = {
            'template': template,
            'variant_id': variant.id if variant else False,
            'img_src': img_src,
        }
        # ¡IMPORTANTE! usar render, no _render
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)