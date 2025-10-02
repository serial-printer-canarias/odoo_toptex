# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

# PNG 1x1 transparente (fallback)
BLANK_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
)

class SpwReport(http.Controller):

    @http.route(['/spw/line_preview/<int:line_id>.png',
                 '/spw/line_preview/<int:line_id>'],
                type='http', auth='public', website=True, cors='*')
    def spw_line_preview(self, line_id, **kw):
        """Devuelve el PNG de personalización para una línea de venta/factura."""
        env = request.env.sudo()

        rec = env['sale.order.line'].browse(line_id)
        if not rec.exists():
            rec = env['account.move.line'].browse(line_id)
            if not rec.exists():
                return request.make_response(BLANK_PNG, [('Content-Type', 'image/png')])

        # 1) Adjuntos PNG ligados a la línea (nombre contiene 'spw')
        att = env['ir.attachment'].search([
            ('res_model', '=', rec._name),
            ('res_id', '=', rec.id),
            ('mimetype', 'ilike', 'image/png'),
            ('name', 'ilike', 'spw')
        ], limit=1)
        if att and att.datas:
            return request.make_response(base64.b64decode(att.datas),
                                         [('Content-Type', 'image/png')])

        # 2) Campos binarios si existen
        data_b64 = False
        if 'spw_png' in rec._fields and rec.spw_png:
            data_b64 = rec.spw_png
        elif 'spw_png_data' in rec._fields and rec.spw_png_data:
            data_b64 = rec.spw_png_data
        if data_b64:
            try:
                return request.make_response(base64.b64decode(data_b64),
                                             [('Content-Type', 'image/png')])
            except Exception:
                pass

        # 3) Fallback
        return request.make_response(BLANK_PNG, [('Content-Type', 'image/png')])