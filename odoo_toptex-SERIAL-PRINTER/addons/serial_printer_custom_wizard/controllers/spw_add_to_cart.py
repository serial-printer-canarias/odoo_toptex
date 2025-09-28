# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

_PX_PNG = (  # 1x1 transparente
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQAB'
    b'JX1nWQAAAABJRU5ErkJggg=='
)

def _normalize_hex(val):
    if not val:
        return ''
    v = val.strip().upper()
    if len(v) == 7 and v.startswith('#'):
        return v
    if len(v) == 6 and not v.startswith('#'):
        return '#'+v
    return v

def _cart_update(variant_id, qty):
    website = request.website
    order = website.sale_get_order(force_create=1)
    product = request.env['product.product'].browse(int(variant_id))
    res = order._cart_update(product_id=product.id, add_qty=float(qty))
    return int(res.get('line_id') or 0)

def _write_line_meta(line_id, tech, svg_color, notes):
    line = request.env['sale.order.line'].browse(int(line_id))
    if not line.exists():
        return
    base_name = line.name.split('\nTécnica', 1)[0]
    tech = (tech or '').strip() or '-'
    svg = _normalize_hex(svg_color) or '#000000'
    text = [base_name, f'Técnica: {tech} | Color SVG: {svg}']
    if (notes or '').strip():
        text.append(notes.strip())
    line.sudo().write({'name': '\n'.join(text)})

def _save_preview(line_id, png_b64):
    if not png_b64:
        return False
    env = request.env
    line = env['sale.order.line'].browse(int(line_id))
    if not line.exists():
        return False
    env['ir.attachment'].sudo().search([
        ('res_model', '=', 'sale.order.line'),
        ('res_id', '=', line.id),
        ('name', 'ilike', f'spw_line_{line.id}.png'),
    ], limit=10).unlink()
    env['ir.attachment'].sudo().create({
        'name': f'spw_line_{line.id}.png',
        'res_model': 'sale.order.line',
        'res_id': line.id,
        'type': 'binary',
        'mimetype': 'image/png',
        'datas': png_b64,
    })
    return True

def _find_preview_b64(line_id):
    att = request.env['ir.attachment'].sudo().search([
        ('res_model', '=', 'sale.order.line'),
        ('res_id', '=', int(line_id)),
        ('mimetype', '=', 'image/png'),
        ('name', 'ilike', f'spw_line_{int(line_id)}.png'),
    ], order='id desc', limit=1)
    return att.datas if att else None

class SPWAddToCart(http.Controller):

    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def add_to_cart_meta_http(self, **kw):
        try:
            variant_id = kw.get('variant_id')
            qty = float(kw.get('qty', 1) or 1)
            tech = kw.get('tech') or ''
            svg_color = kw.get('svg_color') or ''
            notes = kw.get('notes') or ''
            line_id = _cart_update(variant_id, qty)
            if not line_id:
                return request.make_json_response({'ok': False, 'message': 'No se pudo crear la línea.'}, status=400)
            _write_line_meta(line_id, tech, svg_color, notes)
            return request.make_json_response({'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'})
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)}, status=500)

    @http.route('/spw/add_to_cart_meta', type='json', auth='public', csrf=False)
    def add_to_cart_meta(self, **kw):
        variant_id = kw.get('variant_id')
        qty = float(kw.get('qty', 1) or 1)
        tech = kw.get('tech') or ''
        svg_color = kw.get('svg_color') or ''
        notes = kw.get('notes') or ''
        line_id = _cart_update(variant_id, qty)
        if not line_id:
            return {'ok': False, 'message': 'No se pudo crear la línea.'}
        _write_line_meta(line_id, tech, svg_color, notes)
        return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}

    @http.route('/spw/attach_png', type='json', auth='public', csrf=False)
    def attach_png(self, **kw):
        line_id = kw.get('line_id')
        png_b64 = kw.get('png_b64') or ''
        ok = _save_preview(line_id, png_b64)
        return {'ok': bool(ok)}

    @http.route('/spw/attach_png_http', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def attach_png_http(self, **kw):
        try:
            line_id = kw.get('line_id')
            png_b64 = kw.get('png_b64') or ''
            ok = _save_preview(line_id, png_b64)
            return request.make_json_response({'ok': bool(ok)})
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)}, status=500)

    @http.route('/spw/download_png', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def download_png(self, **kw):
        png_b64 = (kw.get('png_b64') or '').strip()
        body = base64.b64decode(png_b64) if png_b64 else base64.b64decode(_PX_PNG)
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', 'attachment; filename="personalizacion.png"'),
            ('Cache-Control', 'no-store'),
        ]
        return request.make_response(body, headers=headers)

    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', methods=['GET'], csrf=False, website=True)
    def line_preview(self, line_id, **kw):
        b64 = _find_preview_b64(line_id)
        body = base64.b64decode(b64) if b64 else base64.b64decode(_PX_PNG)
        headers = [('Content-Type', 'image/png'), ('Cache-Control', 'no-store, max-age=0')]
        return request.make_response(body, headers=headers)