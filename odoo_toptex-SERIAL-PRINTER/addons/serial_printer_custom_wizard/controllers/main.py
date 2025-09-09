# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SerialPrinterCustomizer(http.Controller):

    @http.route(['/personalizacion/<int:product_id>'], type='http', auth='public', website=True, csrf=False)
    def personalizar_producto(self, product_id, **post):
        Product = request.env['product.template'].sudo()
        product = Product.browse(product_id)
        if not product.exists():
            return request.not_found()
        # Renderiza la página con el formulario
        return request.render(
            'serial_printer_custom_wizard.customize_product_template',
            {'product': product}
        )

    @http.route(['/personalizacion/submit/<int:product_id>'], type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def personalizar_submit(self, product_id, **post):
        # Aquí puedes guardar en tu modelo (product.personalizacion, etc.)
        Product = request.env['product.template'].sudo()
        product = Product.browse(product_id)
        if not product.exists():
            return request.not_found()
        # De momento redirigimos de vuelta a la ficha del producto
        return request.redirect('/shop/product/%s' % product_id)