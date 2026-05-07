# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

# PNG transparente de 1x1 para fallback
_BLANK_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQotWAAAAABJRU5ErkJggg=='
)

class SpwCartPreviewController(http.Controller):
    """
    Devuelve la previsualización PNG de una línea del carrito:
    - Primero intenta el campo Binary `spw_png` en sale.order.line
    - Si no existe, busca un adjunto en ir.attachment
    URL: /spw/line_preview/<line_id>.png
    """

    @http.route(
        ['/spw/line_preview/<int:line_id>.png'],
        type='http', auth='public', website=True, methods=['GET'],
        csrf=False, sitemap=False
    )
    def spw_line_preview(self, line_id, **kwargs):
        Line = request.env['sale.order.line'].sudo()
        line = Line.browse(int(line_id))
        if not line.exists():
            return request.not_found()

        # 1) Campo binario directo en la línea
        data = None
        if hasattr(line, 'spw_png') and line.spw_png:
            try:
                data = base64.b64decode(line.spw_png)
            except Exception:
                data = None

        # 2) Fallback: adjunto (por si lo guardas como attachment)
        if not data:
            Att = request.env['ir.attachment'].sudo()
            att = Att.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', '=', 'image/png'),
            ], limit=1, order='id desc')
            if att and att.datas:
                try:
                    data = base64.b64decode(att.datas)
                except Exception:
                    data = None

        if not data:
            data = _BLANK_PNG

        headers = [
            ('Content-Type', 'image/png'),
            # Si quieres cachear en navegador, cambia a max-age=3600, etc.
            ('Cache-Control', 'no-cache, max-age=0'),
        ]
        return request.make_response(data, headers)