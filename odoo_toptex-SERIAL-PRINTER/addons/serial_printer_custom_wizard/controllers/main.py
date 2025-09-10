# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True)
    def customizer_page(self, product_id, **kw):
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/shop')
        return request.render('serial_printer_custom_wizard.spw_customizer_page', {
            'product': product,
        })

    @http.route('/spw/customize/add_to_cart', type='http', auth='public', methods=['POST'], csrf=False)
    def add_to_cart(self, **post):
        try:
            product_id = int(post.get('product_id'))
            qty = float(post.get('qty') or 1)
            technique = post.get('technique') or ''
            position = post.get('position') or ''
            notes = post.get('notes') or ''
            overlay_json = post.get('overlay_json') or '{}'
            product = request.env['product.product'].sudo().browse(product_id)
            if not product.exists():
                return http.Response('{"ok": false, "error":"Producto no encontrado"}', content_type='application/json')

            # Añadir al carrito
            order = request.website.sale_get_order(force_create=True)
            res = order._cart_update(product_id=product.id, add_qty=qty)

            # Adjuntar personalización a la línea creada
            line = request.env['sale.order.line'].sudo().browse(res.get('line_id'))
            vals = {
                'name': f"{line.name}\n[Personalización: {technique}/{position}]",
                'spw_custom_json': {
                    'technique': technique,
                    'position': position,
                    'overlay': overlay_json,
                    'notes': notes,
                }
            }

            # Subida del archivo como adjunto
            file = request.httprequest.files.get('logo')
            if file:
                att = request.env['ir.attachment'].sudo().create({
                    'name': file.filename,
                    'datas': base64.b64encode(file.read()),
                    'mimetype': file.mimetype,
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })
                vals['spw_attachment_id'] = att.id

            line.write(vals)
            return http.Response('{"ok": true}', content_type='application/json')

        except Exception as e:
            return http.Response('{"ok": false, "error": "%s"}' % str(e).replace('"','\''), content_type='application/json')