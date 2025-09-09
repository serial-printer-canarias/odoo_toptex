from odoo import http
from odoo.http import request
import base64

class PortalCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True)
    def public_customizer(self, product_id, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()
        return request.render('serial_printer_custom_wizard.customize_product_template', {
            'product': product,
        })

    @http.route(['/personalizacion/submit'], type='http', auth='public', methods=['POST'], website=True, csrf=True)
    def submit_customization(self, **post):
        # Datos básicos
        product_id = int(post.get('product_id', 0))
        tecnica = post.get('tecnica')
        posicion = post.get('posicion')
        tamano = post.get('tamano')
        color = post.get('color_impresion')
        observ = post.get('observaciones')

        # Fichero
        logo_file = request.httprequest.files.get('logo')
        logo_b64 = False
        if logo_file and logo_file.filename:
            logo_b64 = base64.b64encode(logo_file.read())

        # Crear registro (modelo transitorio o definitivo según tu diseño)
        Personalizacion = request.env['product.personalizacion'].sudo()
        vals = {
            'product_id': product_id,
            'print_technique': tecnica,
            'design_position': posicion,
            'size': tamano,
            'color_impresion': color,
            'notes': observ,
        }
        if logo_b64:
            vals['logo'] = logo_b64
        Personalizacion.create(vals)

        # Volver a la ficha del producto con notificación
        return request.redirect('/shop/product/%s' % product_id)