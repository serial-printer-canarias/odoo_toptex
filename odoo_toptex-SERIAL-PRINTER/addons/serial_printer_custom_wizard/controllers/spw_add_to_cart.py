# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

class SPWCart(http.Controller):

    # -------- Añadir al carrito (JSON) --------
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id=None, qty=1, tech=None, svg_color=None, notes=None, **kw):
        try:
            if not variant_id:
                return {'ok': False, 'message': 'Falta variant_id'}

            variant = request.env['product.product'].sudo().browse(int(variant_id))
            if not variant.exists():
                return {'ok': False, 'message': 'Variante inexistente'}

            order = request.website.sale_get_order(force_create=True)
            res = order._cart_update(product_id=variant.id, add_qty=int(qty or 1))
            line_id = res.get('line_id')
            line = request.env['sale.order.line'].sudo().browse(line_id)

            # Guardar metadatos en el nombre (para visualizar siempre) y notas
            extra = []
            if tech:
                extra.append(f"Técnica: {tech}")
            if svg_color:
                extra.append(f"Color SVG: {svg_color}")
            if extra:
                line.name = (line.name or '') + "\n" + " | ".join(extra)
            if notes:
                line.customer_lead = line.customer_lead  # no-op para asegurar write
                line.note = (line.note or '') + (("\n" if line.note else "") + notes)

            return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    # -------- Fallback HTTP (form-data) --------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        payload = {
            'variant_id': post.get('variant_id'),
            'qty': int(post.get('qty') or 1),
            'tech': post.get('tech'),
            'svg_color': post.get('svg_color'),
            'notes': post.get('notes'),
        }
        data = self.add_to_cart_meta(**payload)
        return request.make_json_response(data)

    # -------- Adjuntar PNG a la línea --------
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id=None, png_b64=None, **kw):
        try:
            if not (line_id and png_b64):
                return {'ok': False, 'message': 'Faltan parámetros'}
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            if not line.exists():
                return {'ok': False, 'message': 'Línea inexistente'}

            att = request.env['ir.attachment'].sudo().create({
                'name': f"spw_line_{line.id}.png",
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'type': 'binary',
                'mimetype': 'image/png',
                'datas': png_b64,  # Odoo espera base64 como str
            })
            return {'ok': True, 'att_id': att.id}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    @http.route('/spw/attach_png_http', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def attach_png_http(self, **post):
        data = self.attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64'))
        return request.make_json_response(data)

    # -------- Servir el preview desde la línea (para el carrito) --------
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, csrf=False)
    def line_preview(self, line_id, **kw):
        Attach = request.env['ir.attachment'].sudo()
        att = Attach.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line_id),
            ('mimetype', '=', 'image/png'),
            ('name', 'like', 'spw_line_%')
        ], order='id desc', limit=1)
        if not att:
            # 1x1 vacío para no romper el layout
            tiny = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAuMBgXr0k6kAAAAASUVORK5CYII=')
            return request.make_response(
                tiny,
                headers=[('Content-Type', 'image/png'), ('Cache-Control', 'no-store, no-cache, max-age=0')]
            )
        return request.make_response(
            base64.b64decode(att.datas or b''),
            headers=[('Content-Type', 'image/png'), ('Cache-Control', 'no-store, no-cache, max-age=0')]
        )

    # -------- Descarga robusta del PNG (iOS/Android/desktop) --------
    @http.route('/spw/download_png', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def download_png(self, **post):
        png_b64 = (post.get('png_b64') or '').strip()
        payload = base64.b64decode(png_b64) if png_b64 else b''
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', 'attachment; filename="personalizacion.png"'),
            ('Cache-Control', 'no-store, no-cache, max-age=0'),
        ]
        return request.make_response(payload, headers=headers)