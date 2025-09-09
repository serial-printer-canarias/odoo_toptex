# controllers/portal_customizer.py
from odoo import http
from odoo.http import request

class PortalCustomizer(http.Controller):

    @http.route(['/mi/personalizaciones/<int:line_id>'], type='http', auth='user', website=True)
    def personalizar_desde_pedido(self, line_id, **kw):
        line = request.env['sale.order.line'].browse(line_id)
        if not line.exists():
            return request.not_found()

        # Buscar personalización existente
        existing = request.env['personalizacion.wizard'].search([
            ('sale_order_line_id', '=', line.id)
        ], limit=1)

        if existing and not existing.editable:
            return request.render('serial_printer_custom_wizard.personalizacion_no_editable', {})

        values = {
            'order_line': line,
            'product': line.product_id,
            'personalizacion': existing
        }
        return request.render('serial_printer_custom_wizard.personalizacion_wizard_template', values)

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True)
    def personalizador_publico(self, product_id, **kw):
        product = request.env['product.product'].browse(product_id)
        if not product.exists():
            return request.not_found()

        values = {
            'product': product
        }
        return request.render('serial_printer_custom_wizard.personalizacion_publica_template', values)