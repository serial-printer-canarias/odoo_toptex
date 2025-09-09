# controllers/portal_customizer.py
from odoo import http
from odoo.http import request

class PortalCustomizer(http.Controller):

    @http.route(['/my/personalizations/<int:order_line_id>'], type='http', auth='user', website=True)
    def personalize_from_order(self, order_line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(order_line_id)
        if not line.exists():
            return request.not_found()

        existing = request.env['product.personalization'].sudo().search([
            ('sale_order_line_id', '=', line.id)
        ], limit=1)

        if existing and not existing.editable:
            return request.render('serial_printer_custom_wizard.personalization_locked', {'record': existing})

        values = {
            'order_line': line,
            'product': line.product_id,
            'personalization': existing,
        }
        return request.render('serial_printer_custom_wizard.form_personalization_portal', values)

    @http.route(['/customize/<int:product_id>'], type='http', auth='public', website=True)
    def public_customizer(self, product_id, **kw):
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        values = {
            'product': product
        }
        return request.render('serial_printer_custom_wizard.form_personalization_public', values)

    @http.route(['/customize/submit'], type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def submit_public_customizer(self, **post):
        # Aquí recogeríamos los datos y crearíamos un lead con adjunto
        name = post.get('name')
        email = post.get('email')
        product_id = int(post.get('product_id'))

        lead = request.env['crm.lead'].sudo().create({
            'name': f"Lead personalización - {name}",
            'email_from': email,
            'description': f"Producto ID: {product_id} - Datos personalizados adjuntos"
        })

        # TODO: manejar logo y datos adjuntos

        return request.redirect('/thanks')