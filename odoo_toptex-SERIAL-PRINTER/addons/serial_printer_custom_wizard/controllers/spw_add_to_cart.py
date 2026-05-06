# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json
from datetime import datetime


def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


class SpwAddToCart(http.Controller):

    def _read_payload(self, post):
        # 1) JSON body (fetch con Content-Type: application/json)
        if request.httprequest.mimetype == 'application/json':
            try:
                raw = request.httprequest.get_data(cache=False, as_text=True) or '{}'
                return json.loads(raw) or {}
            except Exception:
                return {}
        # 2) Form-urlencoded / multipart
        return post or {}

    # ----------- API: añade al carrito + guarda metadatos -----------
    @http.route('/spw/add_to_cart_meta', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart_meta(self, **post):
        vals = self._read_payload(post)

        variant_id = _safe_int(vals.get('variant_id') or vals.get('product_id'))
        qty = float(vals.get('qty') or vals.get('add_qty') or 1)

        tech = (vals.get('tech') or '').strip()
        svg_color = (vals.get('svg_color') or '').strip()
        notes = (vals.get('notes') or '').strip()

        if not variant_id:
            return request.make_json_response({'ok': False, 'error': 'variant_id missing'}, status=400)

        order = request.website.sale_get_order(force_create=True)
        res = order._cart_update(product_id=variant_id, add_qty=qty)

        line_id = res.get('line_id') if isinstance(res, dict) else None
        line_id = _safe_int(line_id)

        if line_id:
            line = request.env['sale.order.line'].sudo().browse(line_id).exists()
            if line:
                line.write({
                    'spw_tech': tech,
                    'spw_svg_color': svg_color,
                    'spw_notes': notes,
                })

        return request.make_json_response({
            'ok': True,
            'line_id': line_id,
            'cart_url': '/shop/cart',
        })

    # ----------- API: adjunta PNG a la línea -----------
    @http.route('/spw/attach_png', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_attach_png(self, **post):
        vals = self._read_payload(post)

        line_id = _safe_int(vals.get('line_id'))
        png_b64 = (vals.get('png_b64') or '').strip()

        if not line_id or not png_b64:
            return request.make_json_response({'ok': False, 'error': 'line_id/png_b64 missing'}, status=400)

        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.make_json_response({'ok': False, 'error': 'line not found'}, status=404)

        raw = base64.b64decode(png_b64)
        att = request.env['ir.attachment'].sudo().create({
            'name': f"spw_{line_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png",
            'type': 'binary',
            'datas': base64.b64encode(raw),
            'mimetype': 'image/png',
            'res_model': 'sale.order.line',
            'res_id': line_id,
        })
        line.write({'spw_png_attachment_id': att.id})

        return request.make_json_response({
            'ok': True,
            'line_id': line_id,
            'attachment_id': att.id,
        })

    # ----------- API: metadatos para preview del carrito -----------
    @http.route('/spw/line_personalizations/<int:line_id>', type='http', auth='public', website=True, csrf=False)
    def spw_line_personalizations(self, line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.make_json_response({'ok': False, 'personalizations': []}, status=404)

        pers = [{
            'tech': line.spw_tech or '',
            'svg_color': line.spw_svg_color or '',
            'notes': line.spw_notes or '',
            'png_url': f"/spw/line_preview/{line.id}.png" if line.spw_png_attachment_id else '',
        }]
        return request.make_json_response({'ok': True, 'personalizations': pers})

    # ----------- Preview PNG -----------
    @http.route(['/spw/line_preview/<int:line_id>.png', '/spw/line_preview/<int:line_id>/<int:i>.png'],
                type='http', auth='public', website=True, csrf=False)
    def spw_line_preview(self, line_id, i=0, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        att = line.spw_png_attachment_id if line else False
        if not att:
            return request.not_found()

        raw = base64.b64decode(att.datas or b'')
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ]
        return request.make_response(raw, headers=headers)

    # ----------- Legacy endpoints -----------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart_meta_http(self, **post):
        return self.spw_add_to_cart_meta(**post)

    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_attach_png_http(self, **post):
        return self.spw_attach_png(**post)
