# serial_printer_custom_wizard/controllers/main.py
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True, csrf=False)
    def customizer(self, product_id, **kwargs):
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        # url de imagen (variant primero; si no, la de la plantilla)
        def img_url(rec, field='image_512'):
            return f"/web/image/{rec._name}/{rec.id}/{field}"

        if product.image_512:
            prod_img = img_url(product, 'image_1024')  # un poco más grande si existe
        else:
            prod_img = img_url(product.product_tmpl_id, 'image_1024')

        values = {
            'product': product,
            'product_image_url': prod_img,
        }
        return request.render('serial_printer_custom_wizard.customizer_page', values)