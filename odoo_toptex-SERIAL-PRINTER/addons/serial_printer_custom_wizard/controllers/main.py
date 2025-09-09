# controllers/main.py
from odoo import http
from odoo.http import request

class SerialPrinterCustomizer(http.Controller):
    @http.route(['/personalizacion/<int:product_id>'], type='http', auth='public', website=True)
    def personalizar_producto(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        return request.render(
            'serial_printer_custom_wizard.customize_product_template',
            {'product': product}
        )