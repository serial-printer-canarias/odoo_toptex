# controllers/main.py
from odoo import http
from odoo.http import request

class SPWController(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True, sitemap=False)
    def personalize(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        values = {
            "product": product,
            "main_object": product,   # <- esto evita el error del editor
        }
        return request.render("serial_printer_custom_wizard.website_personalizar_page", values)