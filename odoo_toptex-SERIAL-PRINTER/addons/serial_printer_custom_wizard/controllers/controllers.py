# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request

class PersonalizationController(http.Controller):

    @http.route('/personalizacion/add_to_cart', type='json', auth='public', website=True, csrf=False)
    def add_to_cart(self, **payload):
        """
        Espera:
        {
          product_id, qty,
          tecnica, tamano,
          posicion?, color_hex?, svg_color?, notas?,
          png_b64?, png_name?
        }
        """
        try:
            product_id = int(payload.get('product_id') or 0)
            qty = float(payload.get('qty') or 1)
            tecnica = (payload.get('tecnica') or '').strip()
            tamano = (payload.get('tamano') or '').strip()
            if not product_id or not tecnica or not tamano:
                return {'ok': False, 'error': 'Faltan datos obligatorios (producto, técnica, tamaño).'}

            order = request.website.sale_get_order(force_create=1)
            res = order._cart_update(product_id=product_id, add_qty=qty)
            line_id = res.get('line_id')
            if not line_id:
                line = order.order_line.filtered(lambda l: l.product_id.id == product_id)[:1]
                line_id = line.id if line else False
            if not line_id:
                return {'ok': False, 'error': 'No se pudo crear la línea en el carrito.'}

            line = request.env['sale.order.line'].sudo().browse(line_id)

            info = {
                'tecnica': tecnica,
                'tamano': tamano,
                'posicion': payload.get('posicion'),
                'color_hex': payload.get('color_hex'),
                'svg_color': payload.get('svg_color'),
                'notas': payload.get('notas'),
                'qty': qty,
            }
            vals = {'x_personalization_json': json.dumps(info, ensure_ascii=False)}

            png_b64 = payload.get('png_b64')  # base64 sin header
            if png_b64:
                vals.update({
                    'x_personalization_png': png_b64,
                    'x_personalization_filename': payload.get('png_name') or 'personalizacion.png',
                })

            # Anotar la info en el nombre de la línea para que se vea en el carrito
            annotate = f"Técnica: {tecnica} | Tamaño: {tamano}"
            if info.get('color_hex'):
                annotate += f" | Color: {info['color_hex']}"
            if info.get('posicion'):
                annotate += f" | Posición: {info['posicion']}"
            if info.get('notas'):
                annotate += f" | Obs: {info['notas']}"

            line.sudo().write({**vals, 'name': f"{line.name}\n{annotate}"})

            return {'ok': True, 'cart_quantity': order.cart_quantity, 'line_id': line.id}
        except Exception as e:
            # Siempre devolvemos JSON para no disparar el popup de error del front
            return {'ok': False, 'error': str(e)}