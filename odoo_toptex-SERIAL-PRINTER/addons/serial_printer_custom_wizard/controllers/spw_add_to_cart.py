# addons/serial_printer_custom_wizard/controllers/spw_add_to_cart.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import base64
from datetime import datetime

class SPWAddToCart(http.Controller):

    @http.route('/spw/add_to_cart', type='json', auth='public', csrf=False, website=True)
    def spw_add_to_cart(self, **kw):
        """Crea adjunto PNG, añade la línea al carrito con la cantidad indicada
        y agrega una nota con técnica, color, observaciones y enlace al PNG."""
        try:
            data = request.jsonrequest or {}
            variant_id = int(data.get('variant_id') or 0)
            template_id = int(data.get('template_id') or 0)
            qty = int(data.get('qty') or 1)

            tech = (data.get('tech') or '').strip()
            svg_color = (data.get('svg_color') or '').strip()
            notes = (data.get('notes') or '').strip()

            size = data.get('size')
            pos_x = data.get('pos_x')
            pos_y = data.get('pos_y')
            rotation = data.get('rotation')

            image_dataurl = data.get('image_dataurl') or ''
            attach_id = False
            attach_link = ''

            # Guardar PNG como adjunto público (si viene)
            if image_dataurl.startswith('data:image'):
                # dejar base64 sin decodificar: Odoo espera base64 en 'datas'
                b64 = image_dataurl.split(',', 1)[-1]
                attach = request.env['ir.attachment'].sudo().create({
                    'name': f'personalizacion_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.png',
                    'type': 'binary',
                    'datas': b64,
                    'mimetype': 'image/png',
                    'public': True,
                })
                attach_id = attach.id
                attach_link = f'/web/content/{attach.id}?download=1'

            # Determinar product_id (variante)
            product_id = variant_id
            if not product_id and template_id:
                tmpl = request.env['product.template'].sudo().browse(template_id)
                if tmpl.exists():
                    product = tmpl._get_first_possible_variant() or tmpl.product_variant_id
                    product_id = product.id

            if not product_id:
                return {'ok': False, 'error': 'No product_id'}

            # Añadir al carrito
            order = request.website.sale_get_order(force_create=True)
            res = order._cart_update(product_id=product_id, add_qty=qty)
            line_id = res.get('line_id')
            line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

            if line and line.exists():
                parts = []
                parts.append((line.name or line.product_id.display_name).strip())
                parts.append('[Personalización]')
                if tech:
                    parts.append(f'• Técnica: {tech}')
                if svg_color:
                    parts.append(f'• Color SVG: {svg_color}')
                parts.append(f'• Tamaño: {size}  PosX: {pos_x}  PosY: {pos_y}  Rot: {rotation}')
                if notes:
                    parts.append(f'• Notas: {notes}')
                if attach_link:
                    parts.append(f'• PNG: {attach_link}')
                line.name = "\n".join(parts)

            return {'ok': True}
        except Exception as e:
            # Log y respuesta controlada
            request.env.cr.rollback()
            request._cr.invalidate_cache()
            return {'ok': False, 'error': str(e)}