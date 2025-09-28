# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import base64
import datetime

PNG_NAME_FMT = "spw_preview_line_%s_%s.png"  # lineId_timestamp

class SpwCustomizer(http.Controller):

    # --- Render de la página del personalizador ---
    @http.route('/spw/customizer', type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        pt = request.env['product.template'].sudo().browse(int(product_id)) if product_id else None
        img_src = ''
        if variant_id:
            img_src = '/web/image/product.product/%s/image_1920' % int(variant_id)
        elif pt and pt.product_variant_id:
            img_src = '/web/image/product.product/%s/image_1920' % pt.product_variant_id.id
        values = {
            'template': pt,
            'variant_id': int(variant_id) if variant_id else False,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # --- Añadir al carrito guardando metadatos (JSON) ---
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta(self, variant_id=None, qty=1, tech='', svg_color='', notes=''):
        try:
            variant = request.env['product.product'].sudo().browse(int(variant_id))
            if not variant.exists():
                return {'ok': False, 'message': 'Variante no encontrada'}

            order = request.website.sale_get_order(force_create=True)
            # Usa la API estándar de Website Sale
            res = order._cart_update(product_id=variant.id, add_qty=float(qty))
            line_id = res.get('line_id') or res.get('line', {}).get('id')
            line = request.env['sale.order.line'].sudo().browse(line_id)

            # Guarda metadatos en campos dedicados y anexa resumen al nombre
            line.sudo().write({
                'spw_tech': tech or False,
                'spw_svg_color': svg_color or False,
                'spw_notes': notes or False,
            })
            extra = "\nTécnica: %s | Color SVG: %s" % (tech or '-', svg_color or '-')
            if extra.strip() not in (line.name or ''):
                line.sudo().write({'name': (line.name or variant.display_name) + extra})

            return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    # Fallback HTTP (por si falla el fetch JSON)
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def add_to_cart_meta_http(self, **post):
        data = self.add_to_cart_meta(
            variant_id=post.get('variant_id'),
            qty=post.get('qty') or 1,
            tech=post.get('tech') or '',
            svg_color=post.get('svg_color') or '',
            notes=post.get('notes') or '',
        )
        return request.make_json_response(data)

    # --- Adjuntar PNG a la línea del carrito ---
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False)
    def attach_png(self, line_id=None, png_b64=None):
        try:
            line = request.env['sale.order.line'].sudo().browse(int(line_id))
            if not line.exists():
                return {'ok': False, 'message': 'Línea no encontrada'}
            if not png_b64:
                return {'ok': False, 'message': 'PNG vacío'}

            ts = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            request.env['ir.attachment'].sudo().create({
                'name': PNG_NAME_FMT % (line.id, ts),
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'type': 'binary',
                'mimetype': 'image/png',
                'datas': png_b64,
            })
            return {'ok': True}
        except Exception as e:
            return {'ok': False, 'message': str(e)}

    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def attach_png_http(self, **post):
        data = self.attach_png(line_id=post.get('line_id'), png_b64=post.get('png_b64'))
        return request.make_json_response(data)

    # --- Servir la última previsualización guardada para una línea ---
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', website=True, csrf=False)
    def line_preview(self, line_id, **kw):
        Att = request.env['ir.attachment'].sudo()
        att = Att.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', int(line_id)),
            ('mimetype', '=', 'image/png'),
        ], order='id desc', limit=1)
        if not att:
            # PNG transparente 1x1
            pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AApMBtH4zLzIAAAAASUVORK5CYII=')
            headers = [
                ('Content-Type', 'image/png'),
                ('Content-Length', str(len(pixel))),
                ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ]
            return request.make_response(pixel, headers=headers)
        raw = base64.b64decode(att.datas or b'')
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ]
        return request.make_response(raw, headers=headers)

    # --- Descarga del PNG generado (compatible iOS/Android/escritorio) ---
    @http.route('/spw/download_png', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def download_png(self, **post):
        b64 = (post.get('png_b64') or '').strip()
        if not b64:
            return request.not_found()
        raw = base64.b64decode(b64)
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Content-Disposition', 'attachment; filename="personalizacion.png"'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ]
        return request.make_response(raw, headers=headers)