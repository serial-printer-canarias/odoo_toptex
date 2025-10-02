# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

# PNG transparente 1x1 como fallback (evita 404/500 en <img>)
BLANK_PNG = base64.b64decode(
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/eeNdt8AAAAASUVORK5CYII='
)

class SpwReport(http.Controller):
    # ---------------------------------------------------------
    # 1) PREVIEW EN CARRITO / LISTAS
    #    /spw/line_preview/<id>.png  -> binario PNG
    # ---------------------------------------------------------
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True)
    def spw_line_preview(self, line_id, **kw):
        """
        Devuelve el PNG de personalización asociado a una sale.order.line.
        Si no existe, responde un PNG 1x1 transparente.
        """
        env = request.env.sudo()
        # Registro puede ser sale.order.line o, por compatibilidad, account.move.line
        sol = env['sale.order.line'].browse(line_id)
        aml = env['account.move.line'].browse(line_id)
        rec = sol if sol.exists() else (aml if aml.exists() else None)

        if not rec:
            return request.make_response(BLANK_PNG, headers=[('Content-Type', 'image/png')])

        # Buscamos adjunto más reciente con nombre tipo spw_* y mimetype imagen
        att = env['ir.attachment'].search([
            ('res_model', '=', rec._name),
            ('res_id', '=', rec.id),
            ('mimetype', 'ilike', 'image'),
            ('name', 'ilike', 'spw%'),
        ], limit=1, order='id desc')

        if not att:
            return request.make_response(BLANK_PNG, headers=[('Content-Type', 'image/png')])

        data = base64.b64decode(att.datas or b'') if att.datas else BLANK_PNG
        return request.make_response(data, headers=[('Content-Type', att.mimetype or 'image/png')])

    # ---------------------------------------------------------
    # 2) GUARDAR PNG EN LA LÍNEA (JSON)
    # ---------------------------------------------------------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def spw_attach_png_json(self, line_id=None, png_b64=None, **kw):
        """
        Guarda el PNG en ir.attachment vinculado a sale.order.line (line_id).
        Devuelve {ok: True, attachment_id: <id>} o {ok: False, message: "..."}.
        """
        try:
            line_id = int(line_id) if line_id else 0
            if not line_id or not png_b64:
                return {'ok': False, 'message': 'missing data'}

            line = request.env['sale.order.line'].sudo().browse(line_id)
            if not line.exists():
                return {'ok': False, 'message': 'line not found'}

            # Limpia anteriores adjuntos spw_* de esa línea (opcional pero evita basura)
            request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('name', 'ilike', 'spw%'),
            ]).unlink()

            # Acepta tanto "xxxx" como "data:image/png;base64,xxxx"
            data_part = png_b64.split('base64,')[-1]

            att = request.env['ir.attachment'].sudo().create({
                'name': 'spw_line_%s.png' % line.id,
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'type': 'binary',
                'mimetype': 'image/png',
                'datas': data_part,
            })
            return {'ok': True, 'attachment_id': att.id}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    # ---------------------------------------------------------
    # 3) GUARDAR PNG EN LA LÍNEA (POST clásico, fallback)
    # ---------------------------------------------------------
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_attach_png_http(self, **post):
        """
        Fallback HTTP para navegadores que bloqueen JSON fetch por CORS/CSRF.
        """
        res = self.spw_attach_png_json(
            line_id=post.get('line_id') or post.get('line') or post.get('lineid'),
            png_b64=post.get('png_b64'),
        )
        return request.make_json_response(res)