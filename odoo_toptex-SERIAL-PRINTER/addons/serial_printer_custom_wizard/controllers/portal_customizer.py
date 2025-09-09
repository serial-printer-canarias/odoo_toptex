import base64
from odoo import http
from odoo.http import request

class PortalCustomizer(http.Controller):

    @http.route(['/customizar/<int:product_id>'], type='http', auth='public', website=True)
    def public_customizer(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        return request.render(
            'serial_printer_custom_wizard.customize_product_template',
            {'product': product}
        )

    @http.route(['/personalizacion/enviar'], type='http', auth='public', methods=['POST'], csrf=True, website=True)
    def submit_personalizacion(self, **post):
        # Producto
        product_id = int(post.get('product_tmpl_id', '0') or 0)
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        # Valores del formulario
        vals = {
            'product_tmpl_id': product.id,
            'tecnica_personalizacion': post.get('tecnica') or 'ninguna',
            'posicion_diseno': post.get('posicion') or False,
            'tamano_diseno': post.get('tamano') or False,
            'color_impresion': post.get('color_impresion') or False,
            'observaciones': post.get('observaciones') or False,
        }

        # Logo (archivo)
        fileobj = request.httprequest.files.get('logo')
        if fileobj:
            vals['logo'] = base64.b64encode(fileobj.read())

        request.env['product.personalizacion'].sudo().create(vals)

        return request.render(
            'serial_printer_custom_wizard.customize_thanks',
            {'product': product}
        )