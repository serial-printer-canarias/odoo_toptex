# -*- coding: utf-8 -*-
import base64
import json
from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response

class SPWCart(http.Controller):

    # ------------------ Helpers ------------------
    def _get_order(self):
        website = request.env['website'].get_current_website()
        return website.sale_get_order(force_create=True)

    def _ok(self, **kw):
        data = {'ok': True}
        data.update(kw)
        return Response(json.dumps(data), content_type='application/json')

    def _bad(self, msg="Error"):
        return Response(json.dumps({'ok': False, 'message': msg}),
                        content_type='application/json', status=400)

    # ------------------ Add meta (JSON) ------------------
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def spw_add_to_cart_meta(self, variant_id=None, qty=1, tech="", svg_color="", notes=""):
        try:
            order = self._get_order()
            qty = int(qty or 1)
            variant_id = int(variant_id)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos'}

        # Añadir al carrito
        res = order._cart_update(product_id=variant_id, add_qty=qty)
        line_id = res.get('line_id') or res.get('line', False)
        if not line_id:
            return {'ok': False, 'message': 'No se pudo crear la línea'}

        line = request.env['sale.order.line'].sudo().browse(int(line_id))
        # Guardamos meta en campos de la línea (si existen), y adicional en name
        updates = {}
        for k, v in [('spw_tech', tech), ('spw_svg_color', svg_color), ('spw_notes', notes)]:
            if k in line._fields:
                updates[k] = v
        if 'spw_meta_json' in line._fields:
            updates['spw_meta_json'] = json.dumps({'tech': tech, 'svg_color': svg_color, 'notes': notes})
        if updates:
            line.write(updates)

        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}

    # ------------------ Add meta (form fallback) ------------------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def spw_add_to_cart_meta_http(self, **post):
        try:
            return self.spw_add_to_cart_meta(
                variant_id=int(post.get('variant_id')),
                qty=int(post.get('qty', 1)),
                tech=post.get('tech', ''),
                svg_color=post.get('svg_color', ''),
                notes=post.get('notes', ''),
            )
        except Exception as e:
            return self._bad('Error en parámetros')

    # ------------------ Attach PNG (JSON) ------------------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def spw_attach_png(self, line_id=None, png_b64=""):
        try:
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada'}
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos'}

        datas = png_b64
        if not datas:
            return {'ok': False, 'message': 'PNG vacío'}

        # Campo binario si existe
        if 'spw_png' in line._fields:
            line.write({'spw_png': datas})

        # Adjunto clásico
        request.env['ir.attachment'].sudo().create({
            'name': 'spw_preview_%s.png' % line.id,
            'datas': datas,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'mimetype': 'image/png',
        })
        return {'ok': True}

    # ------------------ Attach PNG (form fallback) ------------------
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def spw_attach_png_http(self, **post):
        return self.spw_attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64', ''))

    # ------------------ Serve preview by line ------------------
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True)
    def spw_line_preview(self, line_id):
        line = request.env['sale.order.line'].sudo().browse(int(line_id))
        png = None
        # Prioriza campo binario
        if 'spw_png' in line._fields and line.spw_png:
            png = base64.b64decode(line.spw_png)
        else:
            att = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', int(line_id)),
                ('mimetype', '=', 'image/png'),
            ], order='id desc', limit=1)
            if att:
                png = base64.b64decode(att.datas or b'')
        if not png:
            # 1x1 transparente
            png = base64.b64decode(
                b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
            )
        headers = [('Content-Type', 'image/png'), ('Cache-Control', 'no-store')]
        return Response(png, headers=headers)

    # ------------------ Cart JSON (fallback mapping) ------------------
    @http.route('/spw/cart_json', type='http', auth='public', website=True)
    def spw_cart_json(self):
        order = self._get_order()
        lines = []
        for l in order.order_line.sudo():
            lines.append({
                'id': l.id,
                'product_id': l.product_id.id,
                'name': l.name,
                'svg_color': getattr(l, 'spw_svg_color', '') or '',
                'preview_url': '/spw/line_preview/%s.png' % l.id,
            })
        return Response(json.dumps({'lines': lines}), content_type='application/json')