# --- SPW: previews en carrito por línea (multi-foto) ---
from odoo import http
from odoo.http import request
import base64

class SpwCartPreviewController(http.Controller):

    @http.route([
        '/spw/line_preview/<int:line_id>',
        '/spw/line_preview/<int:line_id>.<string:ext>',
        '/spw/line_preview/<int:line_id>-<int:index>',
        '/spw/line_preview/<int:line_id>-<int:index>.<string:ext>',
        '/spw/line_preview/<int:line_id>/<int:index>',
        '/spw/line_preview/<int:line_id>/<int:index>.<string:ext>',
    ], type='http', auth='public', website=True, methods=['GET'])
    def spw_line_preview(self, line_id, index=1, ext=None, **kw):
        # permitir ?i=2 además de los patrones con -2 o /2
        try:
            i = int(kw.get('i', index or 1))
        except Exception:
            i = 1
        if i < 1:
            i = 1

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return request.not_found()

        # Busca adjuntos de la personalización, tolerante a distintas implementaciones
        attachments = []
        # 1) one2many de adjuntos directos
        if 'spw_png_attachment_ids' in line._fields and line.spw_png_attachment_ids:
            attachments = line.spw_png_attachment_ids.sorted('id')
        # 2) one2many de previews con campo attachment_id
        elif 'spw_preview_ids' in line._fields and line.spw_preview_ids:
            attachments = line.spw_preview_ids.mapped('attachment_id')
        # 3) único adjunto (campo many2one)
        elif 'spw_png_attachment_id' in line._fields and line.spw_png_attachment_id:
            attachments = line.spw_png_attachment_id

        # Normaliza a “lista” para indexar
        if hasattr(attachments, '__len__') and not isinstance(attachments, bytes):
            recs = attachments
        else:
            recs = [attachments] if attachments else []

        attach = None
        if recs:
            attach = recs[i-1] if len(recs) >= i else recs[0]

        if not attach:
            return request.not_found()

        data = attach.datas or getattr(attach, 'raw', None)
        if not data:
            return request.not_found()

        try:
            payload = base64.b64decode(data)
        except Exception:
            payload = data

        mimetype = attach.mimetype or 'image/png'
        headers = [
            ('Content-Type', mimetype),
            ('Cache-Control', 'no-store, no-cache, must-revalidate'),
        ]
        return request.make_response(payload, headers)