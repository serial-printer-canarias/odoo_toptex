# -*- coding: utf-8 -*-
import json
from base64 import b64decode, b64encode
from io import BytesIO
from odoo import http
from odoo.http import request

# PIL está disponible en Odoo
from PIL import Image, ImageDraw, ImageFont

def _sanitize_b64(data):
    if not data:
        return ''
    # admite 'data:image/png;base64,.....'
    if isinstance(data, str) and 'base64,' in data:
        return data.split('base64,', 1)[1]
    return data

def _generate_fallback_png(product):
    """Si el cliente no manda PNG, generamos uno desde la imagen del producto."""
    # base transparente si no hay imagen
    if product.image_1920:
        raw = b64decode(product.image_1920)
        im = Image.open(BytesIO(raw)).convert('RGBA')
    else:
        im = Image.new('RGBA', (900, 900), (255, 255, 255, 0))
    draw = ImageDraw.Draw(im)
    # banda blanca semitransparente arriba para anotar
    draw.rectangle([(0, 0), (im.width, 110)], fill=(255, 255, 255, 200))
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((24, 36), "Personalización aplicada", fill=(0, 0, 0, 255), font=font)
    out = BytesIO()
    im.save(out, format='PNG')
    return b64encode(out.getvalue()).decode()

class PersonalizationController(http.Controller):

    @http.route('/personalizacion/add_to_cart', type='json', auth='public', website=True, csrf=False)
    def add_to_cart(self, **payload):
        """
        payload:
          product_id, qty, tecnica, tamano, posicion?, color_hex?, svg_color?, notas?, png_b64?, png_name?
        """
        try:
            product_id = int(payload.get('product_id') or 0)
            qty = float(payload.get('qty') or 1)
            tecnica = (payload.get('tecnica') or '').strip()
            tamano = (payload.get('tamano') or '').strip()

            if not product_id or not tecnica or not tamano:
                return {'ok': False, 'error': 'Faltan: producto, técnica o tamaño.'}

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

            png_b64 = _sanitize_b64(payload.get('png_b64'))
            if not png_b64:
                # Fallback: generamos PNG del propio producto para que SIEMPRE haya imagen
                prod = request.env['product.product'].sudo().browse(product_id)
                png_b64 = _generate_fallback_png(prod)

            vals = {
                'x_personalization_json': json.dumps(info, ensure_ascii=False),
                'x_personalization_png': png_b64,
                'x_personalization_filename': payload.get('png_name') or 'personalizacion.png',
            }

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
            return {'ok': False, 'error': str(e)}