# -*- coding: utf-8 -*-
import json
import base64
import re
from odoo import http
from odoo.http import request

NAME_RE = re.compile(r'^spw_preview_(\d+)_(\d+)\.png$')

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
            line_id = res.get('line_id') or (res.get('line') and res['line'].id)
            line = request.env['sale.order.line'].sudo().browse(line_id)
            if not line or not line.exists():
                return {'ok': False, 'message': 'No se pudo crear la línea'}

            # guarda metadatos visibles en la descripción
            line.sudo().write({
                'spw_tech': tech or '',
                'spw_svg_color': (svg_color or '').upper(),
                'spw_notes': notes or '',
            })
            try:
                line._apply_spw_meta_to_name()
            except Exception:
                # si no está el método heredado, no pasa nada
                pass

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

    def _next_seq_for_line(self, line_id):
        """Busca adjuntos existentes 'spw_preview_<line>_<seq>.png' y devuelve el siguiente seq."""
        Attachment = request.env['ir.attachment'].sudo()
        atts = Attachment.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('name', 'like', f'spw_preview_{int(line_id)}_%')
        ], order='id asc')
        max_seq = 0
        for a in atts:
            m = NAME_RE.match(a.name or '')
            if m:
                try:
                    max_seq = max(max_seq, int(m.group(2)))
                except Exception:
                    pass
        return max_seq + 1

    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id=None, png_b64=None, **kw):
        try:
            if not (line_id and png_b64):
                return {'ok': False, 'message': 'Faltan datos PNG'}
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada'}

            seq = self._next_seq_for_line(line.id)
            att = request.env['ir.attachment'].sudo().create({
                'name': f'spw_preview_{line.id}_{seq}.png',
                'datas': png_b64,
                'mimetype': 'image/png',
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'public': True,
            })
            return {'ok': True, 'attachment_id': att.id, 'seq': seq}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False)
    def attach_png_http(self, **post):
        data = self.attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64'))
        return request.make_response(json.dumps(data), headers=[('Content-Type','application/json')])

    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, sitemap=False)
    def line_preview(self, line_id, **kw):
        """Compat: devuelve la ÚLTIMA preview de la línea, o un pixel si aún no hay."""
        Attachment = request.env['ir.attachment'].sudo()
        att = Attachment.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('name', 'like', f'spw_preview_{int(line_id)}_%')
        ], order='id desc', limit=1)
        if not att:
            pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9WlqZ1sAAAAASUVORK5CYII=')
            return request.make_response(pixel, headers=[('Content-Type','image/png')])
        return request.redirect('/web/image/%d' % att.id)

    @http.route('/spw/line_previews/<int:line_id>.json', type='http', auth='public', website=True, sitemap=False)
    def line_previews_json(self, line_id, **kw):
        """Devuelve TODAS las previews de la línea en orden ascendente."""
        Attachment = request.env['ir.attachment'].sudo()
        atts = Attachment.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('name', 'like', f'spw_preview_{int(line_id)}_%')
        ], order='id asc')
        urls = [f'/web/image/{a.id}' for a in atts]
        body = json.dumps({'ok': True, 'images': urls})
        return request.make_response(body, headers=[('Content-Type','application/json')])

    @http.route('/spw/download_png', type='http', auth='public', website=True, csrf=False)
    def download_png(self, **post):
        png_b64 = post.get('png_b64')
        if not png_b64:
            return request.not_found()
        data = base64.b64decode(png_b64)
        headers = [('Content-Type','image/png'),
                   ('Content-Disposition','attachment; filename="personalizacion.png"')]
        return request.make_response(data, headers=headers)