# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SerialPrinterCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth="public", website=True)
    def personalizar(self, product_id, **kw):
        """Página de personalización con preview"""
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        # Variante inicial (si viene por querystring la respetamos)
        variant_id = kw.get('variant_id')
        if variant_id:
            try:
                variant_id = int(variant_id)
            except Exception:
                variant_id = False
        if not variant_id and product.product_variant_id:
            variant_id = product.product_variant_id.id

        values = {
            'product': product,
            'variants': product.product_variant_ids.sudo(),
            'variant_id': variant_id,
        }
        return request.render('serial_printer_custom_wizard.website_personalizar_page', values)

    @http.route(['/personalizar/add'], type='http', auth='public', website=True, csrf=True)
    def personalizar_add(self, **post):
        """Recoge el formulario y (ejemplo) vuelve a la ficha del producto.
        Aquí puedes crear líneas de pedido, adjuntos, etc.
        """
        product_id = int(post.get('product_id', 0))
        return request.redirect('/shop/product/%s' % product_id)