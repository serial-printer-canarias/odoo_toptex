# -*- coding: utf-8 -*-
import json
import base64
from odoo import http
from odoo.http import request

class SpwAddToCart(http.Controller):

    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id=None, qty=1, tech='', svg_color='', notes='', **kw):
        try:
            variant_id = int(variant_id or 0)
            if not variant_id:
                return {'ok': False, 'message': 'variant_id faltante'}
            variant = request.env['product.product'].sudo().browse(variant_id)
            if not variant.exists():
                return {'ok': False, 'message': 'Variante inexistente'}

            order = request.website.sale_get_order(force_create=1)
            res = order._cart_update(product_id=variant.id, add_qty=int(qty or 1))
            line = res.get('line') or request.env['sale.order.line'].sudo().browse(res.get('line_id'))
            if not line or not line.exists():
                return {'ok': False, 'message': 'No se pudo crear la línea'}

            line.sudo().write({
                'spw_tech': tech or '',
                'spw_svg_color': svg_color or '',
                'spw_notes': notes or '',
            })

            return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        data = self.add_to_cart_meta(
            variant_id=post.get('variant_id'),
            qty=post.get('qty'),
            tech=post.get('tech'),
            svg_color=post.get('svg_color'),
            notes=post.get('notes'),
        )
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id=None, png_b64=None, **kw):
        try:
            if not (line_id and png_b64):
                return {'ok': False, 'message': 'Faltan datos PNG'}
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada'}
            att = request.env['ir.attachment'].sudo().create({
                'name': f'spw_preview_{line.id}.png',
                'datas': png_b64,
                'mimetype': 'image/png',
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'public': True,
            })
            line.sudo().write({'spw_preview_attachment_id': att.id})
            return {'ok': True, 'attachment_id': att.id}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False)
    def attach_png_http(self, **post):
        data = self.attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64'))
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, sitemap=False)
    def line_preview(self, line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return request.not_found()
        att = line.sudo().spw_preview_attachment_id
        if not att:
            # transparente 1x1 si aún no hay adjunto
            pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9WlqZ1sAAAAASUVORK5CYII=')
            return request.make_response(pixel, headers=[('Content-Type','image/png')])
        return request.redirect('/web/image/%d' % att.id)

    @http.route('/spw/download_png', type='http', auth='public', website=True, csrf=False)
    def download_png(self, **post):
        png_b64 = post.get('png_b64')
        if not png_b64:
            return request.not_found()
        data = base64.b64decode(png_b64)
        headers = [('Content-Type','image/png'),
                   ('Content-Disposition','attachment; filename="personalizacion.png"')]
        return request.make_response(data, headers=headers)