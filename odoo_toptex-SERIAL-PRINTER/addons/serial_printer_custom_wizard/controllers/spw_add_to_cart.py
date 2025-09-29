# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from base64 import b64decode
import time, uuid

def _to_int(v, dflt=0):
    try:
        return int(v)
    except Exception:
        return dflt

class SpwCartController(http.Controller):

    # ---------- (1) Crear línea con metadatos ----------
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        """
        Crea una línea de carrito (sin fusionar con otras del mismo SKU) y
        guarda técnica / color / notas. Devuelve line_id.
        """
        vals       = request.jsonrequest or {}
        variant_id = _to_int(vals.get('variant_id'))
        qty        = _to_int(vals.get('qty', 1), 1)
        tech       = (vals.get('tech') or '').strip()
        svg_color  = (vals.get('svg_color') or '').strip()
        notes      = (vals.get('notes') or '').strip()

        # token único por personalización para evitar merge
        token = (vals.get('spw_token') or '').strip() or (uuid.uuid4().hex)

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': _('Bad payload')}

        order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].sudo().browse(variant_id).exists()
        if not product:
            return {'ok': False, 'message': _('Product not found')}

        # PASAR el token por kwargs -> el override del modelo lo usará para NO fusionar
        res = order._cart_update(product_id=product.id, add_qty=qty, spw_token=token)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Guardar metadatos en la línea
        line_vals = {
            'spw_token': token,
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        }
        line.sudo().write(line_vals)

        # Refrescar la descripción visible para que el JS del carrito pueda
        # leer Técnica / Color y pintar la píldora
        base_name = (line.name or '').strip()
        chunks = [c for c in [base_name] if c]
        if tech and f"Técnica:" not in base_name:
            chunks.append(f"Técnica: {tech}")
        if svg_color and f"Color SVG:" not in base_name:
            chunks.append(f"Color SVG: {svg_color}")
        if notes and f"Observaciones:" not in base_name:
            chunks.append(f"Observaciones: {notes}")
        if chunks:
            line.sudo().write({'name': "\n".join(chunks)})

        return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}

    # ---------- (2) Adjuntar PNG ----------
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """
        Adjunta un PNG (base64) a la línea y deja referencia en spw_png_attachment_id.
        """
        data    = request.jsonrequest or {}
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
            'datas': png_b64,   # ya viene en base64
        }
        att = request.env['ir.attachment'].sudo().create(att_vals)
        line.sudo().write({'spw_png_attachment_id': att.id})
        return {'ok': True, 'attachment_id': att.id}

    # ---------- (3) Fallbacks HTTP ----------
    @http.route(['/spw/attach_png_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png_http(self, **post):
        try:
            return request.make_json_response(self.spw_attach_png())
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    @http.route(['/spw/add_to_cart_meta_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta_http(self, **post):
        try:
            return request.make_json_response(self.spw_add_to_cart_meta())
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    # ---------- (4) Servir preview PNG ----------
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview(self, line_id, **kw):
        """
        Devuelve el PNG adjunto. Si no hay, 1x1 transparente.
        """
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        att = line.sudo().spw_png_attachment_id
        if not att:
            att = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', '=', 'image/png'),
                ('name', 'like', 'spw_line_%'),
            ], limit=1)

        if not att:
            # PNG 1x1 transparente
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])