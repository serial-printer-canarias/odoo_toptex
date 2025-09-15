# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request, content_disposition

class SpwCustomizer(http.Controller):

    @http.route('/spw/download_png', type='http', auth='public', website=True, methods=['POST'])
    def spw_download_png(self, png_b64=None, **kw):
        """Recibe PNG base64 y devuelve archivo descargable (iOS compatible)."""
        if not png_b64:
            return request.not_found()
        try:
            data = base64.b64decode(png_b64)
        except Exception:
            return request.not_found()
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(data))),
            ('Content-Disposition', content_disposition('personalizacion.png')),
        ]
        return request.make_response(data, headers)