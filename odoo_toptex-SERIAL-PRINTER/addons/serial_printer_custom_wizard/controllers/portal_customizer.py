# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SPCustomizer(http.Controller):

    @http.route('/personalizar/<model("product.template"):product>', type='http', auth='public', website=True, sitemap=False)
    def website_personalizar(self, product, **kw):
        # Variante seleccionada (si viene de la ficha de producto)
        variant = None
        variant_id = kw.get('variant_id')
        if variant_id:
            variant = request.env['product.product'].sudo().browse(int(variant_id))
            if not variant.exists():
                variant = None

        # URL de imagen base (si hay variante usa su imagen, si no la del template)
        if variant and variant.image_1920:
            base_image_url = f"/web/image/product.product/{variant.id}/image_1920"
        else:
            base_image_url = f"/web/image/product.template/{product.id}/image_1920"

        # Miniaturas de todas las variantes para elegir color/talla visualmente
        variants = request.env['product.product'].sudo().search(
            [('product_tmpl_id', '=', product.id)]
        )
        variant_thumbs = [{
            'id': v.id,
            'name': v.display_name,
            'img': f"/web/image/product.product/{v.id}/image_1920",
        } for v in variants]

        values = {
            'product': product,
            'variant': variant,
            'variant_id': variant.id if variant else (variants[:1].id if variants else False),
            'base_image_url': base_image_url,
            'variant_thumbs': variant_thumbs,
        }
        return request.render('serial_printer_custom_wizard.website_personalizar_page', values)