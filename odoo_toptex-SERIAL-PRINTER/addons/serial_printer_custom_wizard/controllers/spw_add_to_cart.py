# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from base64 import b64decode
import time


def _to_int(v, dflt=0):
    try:
        return int(v)
    except Exception:
        return dflt


class SpwCartController(http.Controller):

    # ====== 1) Crear/actualizar línea con metadatos ======
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        """Crea o actualiza una línea en el carrito y guarda metadatos simples
        (técnica, color SVG, notas). Devuelve line_id y la URL del carrito."""
        vals = request.jsonrequest or {}
        variant_id = _to_int(vals.get('variant_id'))
        qty        = _to_int(vals.get('qty', 1), 1)
        tech       = (vals.get('tech') or '').strip()
        svg_color  = (vals.get('svg_color') or '').strip()
        notes      = (vals.get('notes') or '').strip()

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': _('Bad payload')}

        order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].sudo().browse(variant_id).exists()
        if not product:
            return {'ok': False, 'message': _('Product not found')}

        # _cart_update crea/actualiza línea
        res = order._cart_update(product_id=product.id, add_qty=qty)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)
        # Guarda metadatos en campos propios
        line_vals = {
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        }
        line.sudo().write(line_vals)

        # Asegurar que la descripción visible incluya Técnica/Color (para que el
        # script del carrito pueda detectar #RRGGBB y dibujar la píldora)
        chunks = []
        base_name = (line.name or '').strip()
        if base_name:
            chunks.append(base_name)
        if tech:
            tech_line = f"Técnica: {tech}"
            if tech_line not in base_name:
                chunks.append(tech_line)
        if svg_color:
            color_line = f"Color SVG: {svg_color}"
            if color_line not in base_name:
                chunks.append(color_line)
        if chunks:
            line.sudo().write({'name': "\n".join(chunks)})

        return {
            'ok': True,
            'line_id': line_id,
            'cart_url': '/shop/cart',
        }

    # ====== 2) Adjuntar PNG a la línea ======
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """Adjunta un PNG (en base64) a la línea del carrito y guarda la
        referencia en spw_png_attachment_id."""
        data = request.jsonrequest or {}
        line_id = _to_int(data.get('line_id'))
        png_b64 = (data.get('png_b64') or '').strip()
        if not line_id or not png_b64:
            return {'ok': False, 'message': _('Missing data')}

        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return {'ok': False, 'message': _('Line not found')}

        att_name = f"spw_line_{line.id}_{int(time.time())}.png"
        att_vals = {
            'name': att_name,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': png_b64,  # ya viene en base64
        }
        att = request.env['ir.attachment'].sudo().create(att_vals)
        line.sudo().write({'spw_png_attachment_id': att.id})
        return {'ok': True, 'attachment_id': att.id}

    # Fallback by form POST (por si falla fetch JSON)
    @http.route(['/spw/attach_png_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png_http(self, **post):
        try:
            # post['png_b64'] viene como texto base64
            result = self.spw_attach_png()
            return request.make_json_response(result)
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    # Fallback by form POST
    @http.route(['/spw/add_to_cart_meta_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta_http(self, **post):
        try:
            result = self.spw_add_to_cart_meta()
            return request.make_json_response(result)
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    # ====== 3) Servir la previsualización en el carrito ======
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview(self, line_id, **kw):
        """Devuelve el PNG adjuntado a la línea. Si no existe, 404 o 1x1."""
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        att = line.sudo().spw_png_attachment_id
        if not att:
            # Buscar cualquier adjunto nuestro por si no se grabó en el campo
            att = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', '=', 'image/png'),
                ('name', 'like', 'spw_line_%'),
            ], limit=1)

        if not att:
            # Transparente 1x1 para no romper nada
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])