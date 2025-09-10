from odoo import http
from odoo.http import request

class SpwPersonalizer(http.Controller):
    @http.route('/spw/personalizar/<int:product_id>', type='http', auth='public', website=True)
    def personalizar(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        return request.render('serial_printer_custom_wizard.website_personalizar_page', {'product': product})