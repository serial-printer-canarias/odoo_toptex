# -*- coding: utf-8 -*-
import base64, json
from odoo import http
from odoo.http import request, content_disposition

class SpwCart(http.Controller):

    def _line_id_from_update(self, res):
        if isinstance(res, dict):
            return res.get("line_id") or res.get("line") or res.get("cart_line_id")
        return None

    # Añadir al carrito (JSON)
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id=0, qty=1, tech='', svg_color='', notes=''):
        try:
            variant_id = int(variant_id or 0)
            qty = int(qty or 1)
            if not variant_id or qty <= 0:
                return {'ok': False, 'message': 'Datos inválidos'}

            product = request.env['product.product'].sudo().browse(variant_id)
            if not product.exists():
                return {'ok': False, 'message': 'Producto no existe'}

            order = request.website.sale_get_order(force_create=True)
            upd = order._cart_update(product_id=product.id, add_qty=qty)
            line_id = self._line_id_from_update(upd)

            if not line_id:
                line = request.env['sale.order.line'].sudo().search(
                    [('order_id', '=', order.id), ('product_id', '=', product.id)],
                    order='id desc', limit=1
                )
                line_id = line.id or None

            # Guardar metadatos visibles en la descripción (para leer color en el carrito)
            if line_id:
                line = request.env['sale.order.line'].sudo().browse(line_id)
                extras = []
                if tech: extras.append(f"Técnica: {tech}")
                if svg_color: extras.append(f"Color SVG: {svg_color}")
                if notes: extras.append(f"Notas: {notes}")
                if extras:
                    line.with_context(no_trigger=True).write({
                        'name': (line.name or '') + '\n' + ' | '.join(extras)
                    })
                # Si existen campos técnicos, también guárdalos
                vals = {}
                if 'spw_tech' in line._fields: vals['spw_tech'] = tech
                if 'spw_svg_color' in line._fields: vals['spw_svg_color'] = svg_color
                if 'spw_notes' in line._fields: vals['spw_notes'] = notes
                if vals: line.sudo().write(vals)

            return {
                'ok': True,
                'line_id': line_id,
                'cart_url': request.website._get_shop_cart_url(),
            }
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    # Fallback HTTP
    @http.route('/spw/add_to_cart_meta_http', type='http', methods=['POST'], auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        data = self.add_to_cart_meta(
            variant_id=post.get('variant_id'),
            qty=post.get('qty') or 1,
            tech=post.get('tech') or '',
            svg_color=post.get('svg_color') or '',
            notes=post.get('notes') or '',
        )
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    # Adjuntar PNG a la línea
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id=0, png_b64=''):
        try:
            line_id = int(line_id or 0)
            if not line_id or not png_b64:
                return {'ok': False, 'message': 'falta data'}

            request.env['ir.attachment'].sudo().create({
                'name': 'spw_preview.png',
                'res_model': 'sale.order.line',
                'res_id': line_id,
                'type': 'binary',
                'mimetype': 'image/png',
                'datas': png_b64,
                'public': True,
            })
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    # Fallback HTTP para adjuntar
    @http.route('/spw/attach_png_http', type='http', methods=['POST'], auth='public', website=True, csrf=False)
    def attach_png_http(self, **post):
        data = self.attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64'))
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    # Servir preview en el carrito
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, csrf=False)
    def line_preview(self, line_id, **kw):
        att = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line_id),
            ('mimetype', '=', 'image/png'),
        ], order='id desc', limit=1)
        if not att:
            return request.not_found()
        data = base64.b64decode(att.datas or b'')
        return request.make_response(data, headers=[('Content-Type', 'image/png')])

    # Descarga universal por POST (esto ya lo usa el customizer)
    @http.route('/spw/download_png', type='http', methods=['POST'], auth='public', website=True, csrf=False)
    def download_png(self, **post):
        b64 = (post.get('png_b64') or '').strip()
        if not b64:
            return request.not_found()
        try:
            data = base64.b64decode(b64)
        except Exception:
            return request.not_found()
        return request.make_response(
            data,
            headers=[
                ('Content-Type', 'image/png'),
                ('Content-Disposition', content_disposition('personalizacion.png')),
            ],
        )