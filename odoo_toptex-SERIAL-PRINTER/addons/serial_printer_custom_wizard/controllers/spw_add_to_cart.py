# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request, Response

def _get_last_line(order, product_id):
    lines = order.order_line.filtered(lambda l: l.product_id.id == product_id)
    return lines.sorted(lambda l: (l.create_date, l.id))[-1] if lines else False

class SpwCartApi(http.Controller):

    # ---------- AÑADIR AL CARRITO (JSON) ----------
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False, sitemap=False)
    def add_to_cart_meta(self, variant_id, qty=1, tech="", svg_color="", notes=""):
        variant = request.env['product.product'].sudo().browse(int(variant_id))
        if not variant.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        order = request.website.sale_get_order(force_create=1)
        order._cart_update(product_id=variant.id, add_qty=float(qty))

        line = _get_last_line(order, variant.id)
        if not line:
            return {'ok': False, 'message': 'No se pudo localizar la línea recién creada.'}

        # Meta de personalización en la línea
        line.sudo().write({
            'spw_tech': tech or False,
            'spw_svg_color': (svg_color or '').upper() or False,
            'name': (line.name or '') + (('\nTécnica: %s | Color SVG: %s' % (tech, (svg_color or '').upper())) if (tech or svg_color) else ''),
            'spw_notes': notes or False,
        })

        return {
            'ok': True,
            'line_id': line.id,
            'cart_url': '/shop/cart',
        }

    # ---------- AÑADIR AL CARRITO (HTTP fallback) ----------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False, sitemap=False)
    def add_to_cart_meta_http(self, **post):
        try:
            data = {
                'variant_id': int(post.get('variant_id') or 0),
                'qty': float(post.get('qty') or 1),
                'tech': post.get('tech') or '',
                'svg_color': post.get('svg_color') or '',
                'notes': post.get('notes') or '',
            }
        except Exception:
            return Response('{"ok": false, "message":"Parámetros incorrectos"}', status=400, content_type='application/json')

        res = self.add_to_cart_meta(**data)
        status = 200 if res.get('ok') else 400
        return Response(request.env['ir.qweb']._render_template(
            'web.json', {'json_value': res}), status=status, content_type='application/json')

    # ---------- ADJUNTAR PNG A LA LÍNEA (JSON) ----------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False, sitemap=False)
    def attach_png(self, line_id, png_b64):
        line = request.env['sale.order.line'].sudo().browse(int(line_id))
        if not line.exists():
            return {'ok': False, 'message': 'Línea no encontrada.'}

        png = base64.b64decode(png_b64)
        request.env['ir.attachment'].sudo().create({
            'name': 'spw_preview_%s.png' % line.id,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'datas': base64.b64encode(png),
            'mimetype': 'image/png',
        })
        return {'ok': True}

    # ---------- ADJUNTAR PNG (HTTP fallback) ----------
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False, sitemap=False)
    def attach_png_http(self, **post):
        line_id = int(post.get('line_id') or 0)
        png_b64 = post.get('png_b64') or ''
        res = self.attach_png(line_id=line_id, png_b64=png_b64)
        status = 200 if res.get('ok') else 400
        return Response(request.env['ir.qweb']._render_template(
            'web.json', {'json_value': res}), status=status, content_type='application/json')

    # ---------- SERVIR PREVIEW EN CARRITO ----------
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, csrf=False, sitemap=False)
    def line_preview(self, line_id, **kw):
        Att = request.env['ir.attachment'].sudo()
        att = Att.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('mimetype', '=', 'image/png'),
        ], order='id desc', limit=1)
        if not att:
            # PNG transparente 1x1
            transparent = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMB9U8m1n0AAAAASUVORK5CYII=')
            return Response(transparent, headers=[('Content-Type', 'image/png')])
        return Response(base64.b64decode(att.datas), headers=[('Content-Type', 'image/png')])