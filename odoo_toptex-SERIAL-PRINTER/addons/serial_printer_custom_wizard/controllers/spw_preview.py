# -*- coding: utf-8 -*-
import base64
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
TAG = "[SPW][preview]"

TRANSPARENT_1PX_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAn8B'
    b'Kb9bpgAAAABJRU5ErkJggg=='  # 1x1 px transparente (fallback suave)
)

class SpwPreviewController(http.Controller):
    """Adjunta el PNG a la línea y lo sirve como /spw/line_preview/<line_id>.png"""

    # -------------------- helpers --------------------
    def _decode_png(self, data_uri_or_b64):
        if not data_uri_or_b64:
            return b""
        s = data_uri_or_b64.strip()
        # Permitir dataURL o solo base64
        pos = s.find('base64,')
        if pos != -1:
            s = s[pos + 7:]
        try:
            return base64.b64decode(s)
        except Exception:
            return b""

    def _find_latest_attachment(self, line_id):
        att = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('mimetype', '=', 'image/png'),
        ], order='id desc', limit=1)
        return att

    # -------------------- attach PNG (JSON) --------------------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png_json(self, line_id=None, png_b64=None, **kw):
        try:
            line_id = int(line_id or 0)
            if not line_id:
                return {'ok': False, 'message': 'Falta line_id.'}

            png = self._decode_png(png_b64)
            if not png:
                return {'ok': False, 'message': 'PNG vacío.'}

            line = request.env['sale.order.line'].sudo().browse(line_id)
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada.'}

            vals = {
                'name': 'spw_line_%s.png' % line_id,
                'datas': base64.b64encode(png),
                'mimetype': 'image/png',
                'res_model': 'sale.order.line',
                'res_id': line_id,
                'type': 'binary',
                'public': True,  # visible para usuario web público
                'datas_fname': 'spw_line_%s.png' % line_id,
                'website_id': request.website.id if request.website else False,
            }
            att = request.env['ir.attachment'].sudo().create(vals)
            _logger.info("%s PNG adjuntado -> line=%s att=%s (%d bytes)", TAG, line_id, att.id, len(png))

            return {'ok': True, 'attachment_id': att.id}
        except Exception as e:
            _logger.exception("%s attach_png JSON error: %s", TAG, e)
            return {'ok': False, 'message': 'Error adjuntando PNG.'}

    # -------------------- attach PNG (HTTP fallback) --------------------
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False)
    def attach_png_http(self, **post):
        try:
            line_id = int((post.get('line_id') or '0').strip() or 0)
            png_b64 = (post.get('png_b64') or '').strip()
            res = self.attach_png_json(line_id=line_id, png_b64=png_b64)
            return request.make_json_response(res)
        except Exception as e:
            _logger.exception("%s attach_png HTTP error: %s", TAG, e)
            return request.make_json_response({'ok': False, 'message': 'Error adjuntando PNG (HTTP).'})

    # -------------------- serve preview (PNG) --------------------
    @http.route(['/spw/line_preview/<int:line_id>.png',
                 '/spw/line_preview/<int:line_id>'], type='http',
                auth='public', website=True, csrf=False)
    def line_preview_png(self, line_id, **kw):
        try:
            att = self._find_latest_attachment(line_id)
            if att:
                data = base64.b64decode(att.datas or b'')
                headers = [
                    ('Content-Type', 'image/png'),
                    ('Cache-Control', 'no-cache, no-store, must-revalidate'),
                    ('Pragma', 'no-cache'),
                    ('Expires', '0'),
                    ('X-Content-Type-Options', 'nosniff'),
                    ('Content-Disposition', 'inline; filename="spw_line_%s.png"' % line_id),
                ]
                return request.make_response(data, headers=headers)
            # Fallback: PNG 1x1 para no romper layout; el JS ya intenta usar sessionStorage si viene del customizer
            headers = [('Content-Type', 'image/png'), ('Cache-Control', 'no-cache')]
            return request.make_response(TRANSPARENT_1PX_PNG, headers=headers)
        except Exception as e:
            _logger.exception("%s line_preview error line_id=%s -> %s", TAG, line_id, e)
            headers = [('Content-Type', 'image/png'), ('Cache-Control', 'no-cache')]
            return request.make_response(TRANSPARENT_1PX_PNG, headers=headers)