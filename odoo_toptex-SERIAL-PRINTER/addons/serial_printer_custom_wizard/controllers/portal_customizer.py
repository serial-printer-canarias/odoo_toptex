from odoo import http
from odoo.http import request

class PortalCustomizer(http.Controller):

    @http.route(['/my/personalizations/<int:line_id>'], type='http', auth='user', website=True)
    def personalizar_desde_pedido(self, line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return request.not_found()

        personalizacion = request.env['product.personalizacion'].sudo().search([
            ('sale_order_line_id', '=', line.id)
        ], limit=1)

        if personalizacion and not personalizacion.editable:
            return request.render('serial_printer_custom_wizard.personalizacion_no_editable')

        valores = {
            'order_line': line,
            'product': line.product_id,
            'personalizacion': personalizacion,
        }

        return request.render('serial_printer_custom_wizard.formulario_personalizacion', valores)

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True)
    def personalizador_publico(self, product_id, **kw):
        producto = request.env['product.product'].sudo().browse(product_id)
        if not producto.exists():
            return request.not_found()

        return request.render('serial_printer_custom_wizard.formulario_personalizacion_publica', {
            'product': producto,
        })