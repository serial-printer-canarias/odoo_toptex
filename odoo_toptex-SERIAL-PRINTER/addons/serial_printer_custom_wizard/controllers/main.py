# Directorio: serial_printer_custom_wizard/controllers/main.py

from odoo import http
from odoo.http import request
import base64

class PersonalizacionController(http.Controller):

    @http.route(['/personalizar/guardar'], type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def guardar_personalizacion(self, **post):
        logo_file = post.get('logo')
        values = {
            'tecnica': post.get('tecnica'),
            'tamano_dibujo': post.get('tamano'),
            'color_impresion': post.get('color_impresion'),
            'observaciones': post.get('observaciones') or '',
        }

        if logo_file:
            logo_data = logo_file.read()
            values['logo'] = base64.b64encode(logo_data)
            values['logo_filename'] = logo_file.filename

        request.env['product.personalizacion'].sudo().create(values)
        return request.redirect('/personalizar/gracias')

    @http.route(['/personalizar'], type='http', auth='public', website=True)
    def ver_formulario_personalizacion(self, **kwargs):
        return request.render("serial_printer_custom_wizard.personalizacion_formulario_web", {})

    @http.route(['/personalizar/gracias'], type='http', auth='public', website=True)
    def ver_gracias(self, **kwargs):
        return request.render("serial_printer_custom_wizard.personalizacion_gracias", {})