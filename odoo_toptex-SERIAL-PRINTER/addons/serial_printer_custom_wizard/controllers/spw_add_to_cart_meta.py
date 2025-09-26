# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

class SPWCartMeta(http.Controller):

    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id, qty=1, tech=None, svg_color=None, notes=None, spw_token=None, **kw):
        order = request.website.sale_get_order(force_create=True)
        # CLAVE: pasar spw_token y NO line_id
        res = order._cart_update(product_id=int(variant_id), add_qty=float(qty or 1), spw_token=spw_token)
        line = request.env['sale.order.line'].sudo().browse(res['line_id'])

        # Descripción SOLO de esta línea
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
        Attach = request.env['ir.attachment'].sudo()
        name = 'spw_preview_%s.png' % int(line_id)
        vals = {'name': name, 'res_model': 'sale.order.line', 'res_id': int(line_id),
                'type': 'binary', 'mimetype': 'image/png', 'datas': png_b64}
        ex = Attach.search([('res_model','=','sale.order.line'), ('res_id','=',int(line_id)), ('name','=',name)], limit=1)
        (ex and ex.write(vals)) or Attach.create(vals)
        return {'ok': True}