# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    @http.route(['/spw/customizer',
                 '/spw/customizer/<int:product_id>'],
                type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        """Renderiza la página del personalizador para un producto/variante."""
        ProductT = request.env['product.template'].sudo()
        ProductP = request.env['product.product'].sudo()

        template = None
        variant = None

        # product_id puede llegar como template o como variant: probamos ambos
        if product_id:
            template = ProductT.browse(product_id)
            if not template.exists():
                v = ProductP.browse(product_id)
                if v.exists():
                    variant = v
                    template = v.product_tmpl_id

        # Permitir ?product_template_id= / ?tmpl_id=
        if not template:
            ptid = kw.get('product_template_id') or kw.get('tmpl_id')
            if ptid:
                template = ProductT.browse(int(ptid))

        # Variant explícita por ?variant_id=
        if variant_id and not variant:
            v = ProductP.browse(int(variant_id))
            if v.exists():
                variant = v
                template = v.product_tmpl_id

        # Fallback seguro
        if not template or not template.exists():
            return request.redirect('/shop')

        # Imagen base (si hay variant usamos la suya; si no, la primera variante o la del template)
        if variant and variant.exists():
            img_src = '/web/image/product.product/%s/image_1920' % variant.id
            variant_id_val = variant.id
        else:
            pv = template.product_variant_id
            if pv.exists():
                img_src = '/web/image/product.product/%s/image_1920' % pv.id
                variant_id_val = pv.id
            else:
                img_src = '/web/image/product.template/%s/image_1920' % template.id
                variant_id_val = None

        values = {
            'template': template,
            'variant_id': variant_id_val,
            'img_src': img_src,
            'website': request.website,
        }

        # >>> Forma correcta en Odoo 17/18
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)