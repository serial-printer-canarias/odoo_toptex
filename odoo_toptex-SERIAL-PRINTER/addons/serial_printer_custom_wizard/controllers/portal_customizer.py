from odoo import http
from odoo.http import request

class PortalCustomizer(http.Controller):

    @http.route(['/my/personalizations/<int:line_id>'], type='http', auth='user', website=True)
    def personalize_from_order(self, line_id, **kw):
        line = request.env['sale.order.line'].browse(line_id)
        if not line.exists():
            return request.not_found()

        existing = request.env['product.personalizacion'].search(
            [('sale_order_line_id', '=', line.id)],
            limit=1
        )

        if existing and not existing.editable:
            return request.render('serial_printer_custom_wizard.personalizacion_done', {
                'order_line': line,
                'product': line.product_id,
                'personalizacion': existing,
            })

        values = {
            'order_line': line,
            'product': line.product_id,
            'personalizacion': existing,
        }
        return request.render('serial_printer_custom_wizard.personalizacion_form', values)

    @http.route(['/customize/<int:product_id>'], type='http', auth='public', website=True)
    def public_customizer(self, product_id, **kw):
        product = request.env['product.product'].browse(product_id)
        if not product.exists():
            return request.not_found()
        return request.render('serial_printer_custom_wizard.public_customize_form', {
            'product': product,
        })