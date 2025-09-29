# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from base64 import b64decode
import time
import re

def _to_int(v, dflt=0):
    try:
        return int(v)
    except Exception:
        return dflt

# -------- helpers --------
def _tiny_png():
    # 1x1 transparente
    return b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")

def _att_for_index(line_id, idx):
    Att = request.env['ir.attachment'].sudo()
    name = f"spw_line_{line_id}_{idx}.png"
    rec = Att.search([
        ('res_model', '=', 'sale.order.line'),
        ('res_id', '=', line_id),
        ('mimetype', '=', 'image/png'),
        ('name', '=', name),
    ], limit=1)
    return rec

def _next_idx(line):
    Att = request.env['ir.attachment'].sudo()
    atts = Att.search([
        ('res_model', '=', 'sale.order.line'),
        ('res_id', '=', line.id),
        ('mimetype', '=', 'image/png'),
        ('name', 'like', f"spw_line_{line.id}_"),
    ])
    mx = 0
    for a in atts:
        m = re.search(rf"^spw_line_{line.id}_(\d+)\.png$", a.name or "")
        if m:
            try:
                mx = max(mx, int(m.group(1)))
            except Exception:
                pass
    return mx + 1 if mx >= 0 else 1

def _append_or_replace_block(base_text, idx, tech, color, notes):
    base_text = (base_text or "").strip()
    # quita bloque existente con ese N (si lo hubiera)
    pat = re.compile(rf"—\s*Personalización\s*{idx}\s*—[\s\S]*?(?=—\s*Personalización\s*\d+\s*—|$)")
    base_text = pat.sub("", base_text).strip()

    lines = [f"— Personalización {idx} —"]
    if tech:
        lines.append(f"Técnica: {tech}")
    if color:
        lines.append(f"Color SVG: {color}")
    if notes:
        lines.append(f"Observaciones: {notes}")
    block = "\n".join(lines)

    return (base_text + ("\n" if base_text else "") + block).strip()

class SpwCartController(http.Controller):

    # ====== 1) Crear/actualizar línea y devolver índice N ======
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        vals = request.jsonrequest or {}
        variant_id = _to_int(vals.get('variant_id'))
        qty        = _to_int(vals.get('qty', 1), 1)
        tech       = (vals.get('tech') or '').strip()
        svg_color  = (vals.get('svg_color') or '').strip()
        notes      = (vals.get('notes') or '').strip()
        idx        = _to_int(vals.get('i'), 0)  # opcional: índice pedido por el front

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': _('Bad payload')}

        order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].sudo().browse(variant_id).exists()
        if not product:
            return {'ok': False, 'message': _('Product not found')}

        res = order._cart_update(product_id=product.id, add_qty=qty)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Decide índice (N) si no vino uno
        if not idx:
            idx = _next_idx(line)

        # Guarda campos "últimos" (compat.)
        line_vals = {
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        }
        line.sudo().write(line_vals)

        # Inserta/actualiza bloque “— Personalización N — …” en el name
        new_name = _append_or_replace_block(line.name, idx, tech, svg_color, notes)
        if new_name != (line.name or ""):
            line.sudo().write({'name': new_name})

        return {
            'ok': True,
            'line_id': line_id,
            'i': idx,                 # <-- devuelve N al front para adjuntar el PNG correcto
            'cart_url': '/shop/cart',
        }

    # ====== 2) Adjuntar PNG a la línea con índice N ======
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        data = request.jsonrequest or {}
        line_id = _to_int(data.get('line_id'))
        png_b64 = (data.get('png_b64') or '').strip()
        idx     = _to_int(data.get('i'))  # requerido para multi

        if not line_id or not png_b64:
            return {'ok': False, 'message': _('Missing data')}
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return {'ok': False, 'message': _('Line not found')}

        if not idx:
            idx = _next_idx(line)

        att_name = f"spw_line_{line.id}_{idx}.png"
        att_vals = {
            'name': att_name,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': png_b64,  # ya en base64
        }
        att = request.env['ir.attachment'].sudo().create(att_vals)

        # Compatibilidad: guarda el último también en el campo single
        try:
            line.sudo().write({'spw_png_attachment_id': att.id})
        except Exception:
            pass

        return {'ok': True, 'attachment_id': att.id, 'i': idx}

    # Fallbacks HTTP (por si el fetch JSON falla)
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

    # ====== 3) Endpoints para servir la previsualización N ======
    @http.route([
        '/spw/line_preview/<int:line_id>-<int:idx>.png',      # usado por el JS nuevo
        '/spw/line_preview/<int:line_id>_<int:idx>.png',      # compat
        '/spw/line_preview/<int:line_id>/<int:idx>.png',      # compat
    ], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview_idx(self, line_id, idx, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()
        att = _att_for_index(line_id, idx)
        if not att:
            return request.make_response(_tiny_png(), headers=[('Content-Type', 'image/png')])
        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])

    # Compatibilidad: sin índice devuelve el "último" o 1x1
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview_last(self, line_id, **kw):
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()
        att = getattr(line.sudo(), 'spw_png_attachment_id', False)
        if not att:
            # último por nombre si existe
            idx = _next_idx(line) - 1
            if idx >= 1:
                att = _att_for_index(line.id, idx)
        if not att:
            return request.make_response(_tiny_png(), headers=[('Content-Type', 'image/png')])
        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])