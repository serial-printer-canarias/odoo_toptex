# -*- coding: utf-8 -*-
import logging
import base64

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
TAG = "[SPW][preview]"

class SpwPreviewController(http.Controller):
    # ------------------------------------------------------------
    # Guarda el PNG de la personalización en un adjunto de la línea
    # ------------------------------------------------------------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png_json(self, line_id=None, png_b64=None, **kw):
        try:
            line_id = int(line_id or 0)
            if not line_id or not png_b64:
                return {'ok': False, 'message': 'Faltan parámetros.'}

            line = request.env['sale.order.line'].sudo().browse(line_id)
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada.'}

            name = f"spw_line_{line_id}.png"

            # Eliminar versiones previas para esta línea (opcional)
            request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line_id),
                ('name', 'ilike', f"spw_line_{line_id}%"),
            ]).unlink()

            request.env['ir.attachment'].sudo().create({
                'name': name,
                'res_model': 'sale.order.line',
                'res_id': line_id,
                'type': 'binary',
                'mimetype': 'image/png',
                'datas': png_b64,  # ya viene en base64
            })

            _logger.info("%s PNG attached line=%s (%s bytes b64)", TAG, line_id, len(png_b64))
            return {'ok': True}
        except Exception as e:
            _logger.exception("%s attach_png error: %s", TAG, e)
            return {'ok': False, 'message': 'Error guardando PNG.'}

    # Fallback HTTP (form-data)
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False)
    def attach_png_http(self, **post):
        try:
            line_id = int((post.get('line_id') or '0').strip() or 0)
            png_b64 = (post.get('png_b64') or '').strip()
            res = self.attach_png_json(line_id=line_id, png_b64=png_b64)
            return request.make_json_response(res)
        except Exception as e:
            _logger.exception("%s attach_png_http error: %s", TAG, e)
            return request.make_json_response({'ok': False, 'message': 'Error guardando PNG (HTTP).'})

    # ------------------------------------------------------------
    # Devuelve el PNG para una línea concreta
    #   URL: /spw/line_preview/<line_id>.png
    # ------------------------------------------------------------
    @http.route(['/spw/line_preview/<int:line_id>.png',
                 '/spw/line_preview/<int:line_id>'], type='http',
                auth='public', website=True, csrf=False)
    def line_preview(self, line_id, **kw):
        try:
            Att = request.env['ir.attachment'].sudo()
            att = Att.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line_id),
                ('mimetype', 'ilike', 'image/'),
            ], order='id desc', limit=1)

            if not att:
                _logger.warning("%s no attachment for line=%s", TAG, line_id)
                return request.not_found()

            content = base64.b64decode(att.datas or b'')
            headers = [
                ('Content-Type', att.mimetype or 'image/png'),
                ('Cache-Control', 'no-store, max-age=0'),
            ]
            return request.make_response(content, headers=headers)
        except Exception as e:
            _logger.exception("%s line_preview error line=%s: %s", TAG, line_id, e)
            return request.not_found()