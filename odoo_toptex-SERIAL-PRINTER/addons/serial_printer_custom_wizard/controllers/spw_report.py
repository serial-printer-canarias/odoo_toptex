# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

# PNG transparente 1x1 como fallback (evita 404)
BLANK_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAA'
    b'AAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
)

class SpwReport(http.Controller):

    @http.route('/spw/line_preview/<int:line_id>.png', type='http',
                auth='public', website=True, csrf=False)
    def spw_line_preview(self, line_id, **kw):
        """Devuelve el PNG de personalización de la línea.
        Si no existe, responde 1x1 transparente (sin 404)."""
        env = request.env
        # sale.order.line o account.move.line
        sol = env['sale.order.line'].sudo().browse(line_id)
        aml = env['account.move.line'].sudo().browse(line_id)
        rec = sol if sol.exists() else (aml if aml.exists() else None)
        if not rec:
            return request.make_response(BLANK_PNG, headers=[('Content-Type', 'image/png')])

        # 1) adjunto de imagen asociado a la línea (lo que subimos en el carrito)
        att = env['ir.attachment'].sudo().search([
            ('res_model', '=', rec._name),
            ('res_id', '=', rec.id),
            ('mimetype', 'ilike', 'image/%'),
            ('name', 'ilike', 'spw')
        ], order='id desc', limit=1)

        if att and att.datas:
            data = base64.b64decode(att.datas)
            return request.make_response(
                data,
                headers=[('Content-Type', 'image/png'), ('Cache-Control', 'no-store')]
            )

        # 2) campo binario opcional en la línea (si existiera)
        if hasattr(rec, 'spw_png_b64') and rec.spw_png_b64:
            try:
                data = base64.b64decode(rec.spw_png_b64)
                return request.make_response(
                    data,
                    headers=[('Content-Type', 'image/png'), ('Cache-Control', 'no-store')]
                )
            except Exception:
                pass

        # 3) fallback
        return request.make_response(BLANK_PNG, headers=[('Content-Type', 'image/png')])