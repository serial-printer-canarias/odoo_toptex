# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class PersonalizacionController(http.Controller):

    @http.route(
        '/personalizacion/producto/<model("product.template"):product>',
        type='http', auth='public', website=True)
    def mostrar_formulario(self, product, **kw):
        valores = {'product': product}
        return request.render(
            'serial_printer_custom_wizard.customize_product_template',
            valores
        )

    @http.route(
        '/personalizacion/submit',
        type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def enviar_formulario(self, **post):
        # Datos mínimos
        vals = {
            'product_id': int(post.get('product_id', 0)) if post.get('product_id') else False,
            'tecnica_personalizacion': post.get('tecnica'),
            'posicion_disenyo': post.get('posicion'),
            'tamano_disenyo': post.get('tamano'),
            'color_impresion': post.get('color_impresion'),
            'notas': post.get('observaciones'),
        }
        # Crea el registro (si el modelo existe)
        request.env['product.personalizacion'].sudo().create(vals)
        # Redirige a la ficha del producto
        if vals['product_id']:
            return request.redirect('/shop/product/%s' % vals['product_id'])
        return request.redirect('/shop')