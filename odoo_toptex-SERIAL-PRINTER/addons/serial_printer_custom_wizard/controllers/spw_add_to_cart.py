# -*- coding: utf-8 -*-
import json
import base64
from odoo import http
from odoo.http import request

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        return d

class SPWAddToCart(http.Controller):

    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, **payload):
        variant_id = _int(payload.get('variant_id'))
        qty        = _int(payload.get('qty') or 1, 1)
        tech       = payload.get('tech') or ''
        svg_color  = payload.get('svg_color') or ''
        notes      = payload.get('notes') or ''

        if not variant_id:
            return {'ok': False, 'message': 'variant_id requerido'}

        PP = request.env['product.product'].sudo()
        variant = PP.browse(variant_id)
        if not variant.exists():
            return {'ok': False, 'message': 'Variante no existe'}

        order = request.website.sale_get_order(force_create=1)
        res = order._cart_update(product_id=variant.id, add_qty=qty)
        line = request.env['sale.order.line'].sudo().browse(res.get('line_id'))

        meta = {'tech': tech, 'svg_color': svg_color, 'notes': notes}
        line.write({'spw_meta': json.dumps(meta), 'spw_color': svg_color})

        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}

    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **kw):
        data = self.add_to_cart_meta(**kw)
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, **payload):
        line_id = _int(payload.get('line_id'))
        png_b64 = (payload.get('png_b64') or '').strip()
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return {'ok': False, 'message': 'Línea no encontrada'}

        line.write({'spw_preview': png_b64})
        request.env['ir.attachment'].sudo().create({
            'name': 'spw_preview_%s.png' % line.id,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'mimetype': 'image/png',
            'type': 'binary',
            'datas': png_b64,
        })
        return {'ok': True}

    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False)
    def attach_png_http(self, **kw):
        data = self.attach_png(**kw)
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True)
    def line_preview(self, line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id)
        data = line.spw_preview
        if not data:
            att = request.env['ir.attachment'].sudo().search([
                ('res_model','=','sale.order.line'),
                ('res_id','=', line_id),
                ('name','=','spw_preview_%s.png' % line_id),
            ], limit=1)
            data = att.datas if att else False

        if not data:
            data = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                                    b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
                                    b'\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01'
                                    b'\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82')
        return request.make_response(base64.b64decode(data), headers=[('Content-Type','image/png')])