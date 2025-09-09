from odoo import http
from odoo.http import request

class SerialPrinterWebsite(http.Controller):
    @http.route('/personalizar/<int:product_tmpl_id>', type='http', auth='public', website=True)
    def personalizar_producto(self, product_tmpl_id, **kw):
        product = request.env['product.template'].sudo().browse(product_tmpl_id)
        if not product.exists():
            return request.not_found()
        return request.render('serial_printer_custom_wizard.website_personalizar_page', {
            'product': product
        })