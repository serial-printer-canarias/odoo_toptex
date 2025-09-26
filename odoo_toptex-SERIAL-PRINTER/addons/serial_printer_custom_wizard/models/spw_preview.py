# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request, content_disposition

class SPWPreviewController(http.Controller):

    @http.route('/spw/line_preview/<int:line_id>', type='http', auth='public', website=True)
    def spw_line_preview(self, line_id, i=1, **kw):
        """Devuelve la i-ésima preview (1-based) de la línea."""
        i = int(i or 1)
        if i < 1:
            i = 1

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return request.not_found()

        # Buscamos por nombre estable: spw_preview_<line_id>_<i>.* (png/webp/jpg)
        Attach = request.env['ir.attachment'].sudo()
        attach = Attach.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('type', '=', 'binary'),
            ('name', 'like', 'spw_preview_%s_%s' % (line.id, i)),
        ], limit=1, order='id desc')

        # Fallback: la primera
        if not attach:
            attach = Attach.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('type', '=', 'binary'),
                ('name', 'like', 'spw_preview_%s_1' % line.id),
            ], limit=1, order='id desc')

        if not attach:
            return request.not_found()

        data = base64.b64decode(attach.datas or b'')
        mt = attach.mimetype or 'image/png'
        return request.make_response(
            data,
            headers=[
                ('Content-Type', mt),
                ('Content-Disposition', content_disposition(attach.name)),
                ('Cache-Control', 'no-store, max-age=0'),
            ],
        )