# addons/serial_printer_custom_wizard/controllers/spw_add_to_cart.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime

class SPWAddToCart(http.Controller):

    @http.route('/spw/add_to_cart', type='json', auth='public', csrf=False, website=True)
    def spw_add_to_cart(self, **kw):
        """
        Espera JSON:
          variant_id | template_id, qty,
          tech, svg_color, notes,
          size, pos_x, pos_y, rotation,
          image_dataurl (data:image/png;base64,...)

        Añade línea al carrito con 'qty' y deja la personalización
        documentada (y link público al PNG generado).
        """
        try:
            data = request.jsonrequest or {}
            variant_id = int(data.get('variant_id') or 0)
            template_id = int(data.get('template_id') or 0)
            qty = int(data.get('qty') or 1)

            tech      = (data.get('tech') or '').strip()
            svg_color = (data.get('svg_color') or '').strip()
            notes     = (data.get('notes') or '').strip()

            size     = data.get('size')
            pos_x    = data.get('pos_x')
            pos_y    = data.get('pos_y')
            rotation = data.get('rotation')

            img = (data.get('image_dataurl') or '')
            attach_link = ''

            # Guardar PNG si nos llegó
            if img.startswith('data:image'):
                b64 = img.split(',', 1)[-1]
                att = request.env['ir.attachment'].sudo().create({
                    'name': f'personalizacion_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.png',
                    'type': 'binary',
                    'datas': b64,
                    'mimetype': 'image/png',
                    'public': True,
                })
                attach_link = f'/web/content/{att.id}?download=1'

            # Resolver variante a partir de template si hace falta
            product_id = variant_id
            if not product_id and template_id:
                tmpl = request.env['product.template'].sudo().browse(template_id)
                if tmpl.exists():
                    product = tmpl._get_first_possible_variant() or tmpl.product_variant_id
                    product_id = product.id

            if not product_id:
                return {'ok': False, 'error': 'No se pudo resolver el producto.'}

            order = request.website.sale_get_order(force_create=True)
            res = order._cart_update(product_id=product_id, add_qty=qty)
            line_id = res.get('line_id')
            line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

            if line and line.exists():
                lines = []
                lines.append((line.name or line.product_id.display_name).strip())
                lines.append('[Personalización]')
                if tech:      lines.append(f'• Técnica: {tech}')
                if svg_color: lines.append(f'• Color SVG: {svg_color}')
                lines.append(f'• Tamaño: {size}  PosX: {pos_x}  PosY: {pos_y}  Rot: {rotation}')
                if notes:     lines.append(f'• Notas: {notes}')
                if attach_link:
                    lines.append(f'• PNG: {attach_link}')
                line.name = "\n".join(lines)

            return {'ok': True}
        except Exception as e:
            request.env.cr.rollback()
            return {'ok': False, 'error': str(e)}