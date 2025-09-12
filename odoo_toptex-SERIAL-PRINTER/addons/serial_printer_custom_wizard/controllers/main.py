# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SPWCustomizer(http.Controller):

    @http.route(['/spw/customize', '/shop/customize'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, variant_id=None, tmpl_id=None, product_id=None, **kw):
        """
        Página del personalizador.
        - Si llega variant_id: usamos esa variante y su imagen.
        - Si no, usamos el template indicado (tmpl_id o product_id).
        """
        Product = request.env['product.product'].sudo()
        Template = request.env['product.template'].sudo()

        def _to_int(v):
            try:
                return int(v)
            except Exception:
                return None

        v_id = _to_int(variant_id)
        t_id = _to_int(tmpl_id) or _to_int(product_id)

        variant = None
        template = None

        if v_id:
            variant = Product.browse(v_id).exists()
            if variant:
                template = variant.product_tmpl_id
        if not template and t_id:
            template = Template.browse(t_id).exists()
        if not template and not variant:
            return request.redirect('/shop')

        # Imagen base: variante si hay, si no template
        if variant:
            base_img_url = f'/web/image/product.product/{variant.id}/image_1024'
        else:
            base_img_url = f'/web/image/product.template/{template.id}/image_1024'

        values = {
            'product': template,
            'product_tmpl': template,
            'variant': variant,
            'base_image_url': base_img_url,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)