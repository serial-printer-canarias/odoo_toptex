# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request, content_disposition

class SPWCartMeta(http.Controller):

    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id, qty=1, tech=None, svg_color=None, notes=None, spw_token=None, **kw):
        """
        No crea línea (ya la crea /shop/cart/update_json). Solo ajusta el 'name' de ESA línea
        cuando qty=0, pero mantenemos compatibilidad si qty>0.
        """
        order = request.website.sale_get_order(force_create=True)
        # Si qty > 0, podría crear línea; si es 0 solo devuelve order y seguimos.
        res = order._cart_update(product_id=int(variant_id), add_qty=float(qty or 0), spw_token=spw_token) if float(qty or 0) else {}
        line_id = res.get('line_id')

        # Si no tenemos line_id porque qty=0, intentamos localizar la última línea con ese token
        if not line_id and spw_token:
            line = request.env['sale.order.line'].sudo().search([
                ('order_id', '=', order.id),
                ('product_id', '=', int(variant_id)),
                ('spw_token', '=', spw_token),
            ], order='id desc', limit=1)
            line_id = line.id if line else False

        if not line_id:
            return {'ok': True, 'line_id': False, 'cart_url': '/shop/cart'}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Construir meta SOLO para esta personalización
        base_name = (line.name or '').split('\n')[0]
        meta = []
        if tech: meta.append('Técnica: %s' % tech)
        if svg_color: meta.append('Color SVG: %s' % svg_color)
        if notes: meta.append('Notas: %s' % notes)
        if meta:
            line.write({'name': base_name + '\n' + ' | '.join(meta)})

        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}

    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id, png_b64, **kw):
        """Adjunta/actualiza un PNG por línea."""
        if not line_id or not png_b64:
            return {'ok': False}
        Attach = request.env['ir.attachment'].sudo()
        name = 'spw_preview_%s.png' % int(line_id)
        vals = {
            'name': name,
            'res_model': 'sale.order.line',
            'res_id': int(line_id),
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': png_b64,
        }
        ex = Attach.search([
            ('res_model','=','sale.order.line'),
            ('res_id','=',int(line_id)),
            ('name','=',name),
        ], limit=1)
        (ex and ex.write(vals)) or Attach.create(vals)
        return {'ok': True}

    # (opcional) servir el PNG si no lo tienes en otro controlador
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True)
    def spw_line_preview_png(self, line_id, **kw):
        Attach = request.env['ir.attachment'].sudo()
        name = 'spw_preview_%s.png' % line_id
        att = Attach.search([
            ('res_model','=','sale.order.line'),
            ('res_id','=',line_id),
            ('type','=','binary'),
            ('name','=',name),
        ], limit=1)
        if not att:
            return request.not_found()
        data = base64.b64decode(att.datas or b'')
        return request.make_response(
            data,
            headers=[
                ('Content-Type','image/png'),
                ('Content-Disposition', content_disposition(name)),
                ('Cache-Control','no-store, max-age=0'),
            ],
        )