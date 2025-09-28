# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from base64 import b64decode
import re
import time


def _to_int(v, dflt=0):
    try:
        return int(v)
    except Exception:
        return dflt


HEX_RE = re.compile(r'Color\s*SVG\s*:\s*#([0-9a-fA-F]{3,8})')


def _strip_b64_header(data_uri_or_b64: str) -> str:
    """Quita 'data:image/png;base64,' si viene como DataURL."""
    if not data_uri_or_b64:
        return ''
    if ',' in data_uri_or_b64 and ';base64' in data_uri_or_b64:
        return data_uri_or_b64.split(',', 1)[1]
    return data_uri_or_b64


def _count_personalizations_in_text(text: str) -> int:
    """Cuenta cuántas personalizaciones hay mirando 'Color SVG: #xxxxxx'."""
    if not text:
        return 0
    return len(HEX_RE.findall(text))


def _next_seq_for_line(line) -> int:
    """Calcula el siguiente índice (seq) de personalización para la línea."""
    # 1) Intenta por el texto (lo que ve el cliente y usa el inyectador)
    n_from_text = _count_personalizations_in_text(line.name or '')

    # 2) Cuenta adjuntos ya guardados con nuestro prefijo
    ats = request.env['ir.attachment'].sudo().search_count([
        ('res_model', '=', 'sale.order.line'),
        ('res_id', '=', line.id),
        ('mimetype', '=', 'image/png'),
        ('name', 'like', 'spw_line_%'),
    ])

    # El siguiente índice es el mayor de ambos + 1, para no solaparnos
    return max(n_from_text, ats) + 1


class SpwCartController(http.Controller):

    # =========================================================
    # 1) Crear/actualizar línea y AÑADIR un bloque de metadatos
    # =========================================================
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        """Crea/actualiza una línea y AÑADE la personalización como nuevo bloque.
        Devuelve { ok, line_id, seq, cart_url }.
        """
        vals = request.jsonrequest or {}
        variant_id = _to_int(vals.get('variant_id'))
        qty        = _to_int(vals.get('qty', 1), 1)
        tech       = (vals.get('tech') or '').strip()
        svg_color  = (vals.get('svg_color') or '').strip()   # ej '#D62828'
        notes      = (vals.get('notes') or '').strip()

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': _('Bad payload')}

        order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].sudo().browse(variant_id).exists()
        if not product:
            return {'ok': False, 'message': _('Product not found')}

        # _cart_update crea/actualiza línea del mismo SKU (sumará qty)
        res = order._cart_update(product_id=product.id, add_qty=qty)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Próximo índice de personalización para esta línea
        seq = _next_seq_for_line(line)

        # Construimos un bloque legible (el inyectador detecta Color SVG)
        block_lines = []
        block_lines.append(f"— Personalización {seq} —")
        if tech:
            block_lines.append(f"Técnica: {tech}")
        if svg_color:
            block_lines.append(f"Color SVG: {svg_color}")
        if notes:
            block_lines.append(f"Obs: {notes}")
        block_text = "\n".join(block_lines)

        # Evitar duplicar si ya existe exactamente ese bloque (idempotencia)
        current_name = (line.name or '').strip()
        if block_text not in current_name:
            new_name = (current_name + ("\n\n" if current_name else "") + block_text).strip()
            line.sudo().write({'name': new_name})

        # Guarda también en campos propios (si los tienes para backoffice)
        to_write = {}
        if tech:
            to_write['spw_tech'] = tech
        if svg_color:
            to_write['spw_svg_color'] = svg_color
        if notes:
            to_write['spw_notes'] = notes
        if to_write:
            line.sudo().write(to_write)

        return {'ok': True, 'line_id': line.id, 'seq': seq, 'cart_url': '/shop/cart'}

    # =====================================
    # 2) Adjuntar PNG a la línea (con índice)
    # =====================================
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """Adjunta un PNG (base64) a la línea con un índice 'seq' (1..n).
        Si no se envía 'seq', lo calcula automáticamente.
        """
        data = request.jsonrequest or {}
        line_id = _to_int(data.get('line_id'))
        png_b64 = _strip_b64_header((data.get('png_b64') or '').strip())
        seq     = _to_int(data.get('seq') or data.get('i') or data.get('idx'))

        if not line_id or not png_b64:
            return {'ok': False, 'message': _('Missing data')}

        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return {'ok': False, 'message': _('Line not found')}

        if not seq:
            seq = _next_seq_for_line(line)

        att_name = f"spw_line_{line.id}_{int(seq)}.png"
        att_vals = {
            'name': att_name,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': png_b64,  # ya base64 puro
        }
        att = request.env['ir.attachment'].sudo().create(att_vals)

        # Mantén un campo "último adjunto" para compatibilidad
        if not getattr(line, 'spw_png_attachment_id', False):
            line.sudo().write({'spw_png_attachment_id': att.id})
        else:
            # opcional: actualiza siempre al último
            line.sudo().write({'spw_png_attachment_id': att.id})

        return {'ok': True, 'attachment_id': att.id, 'seq': seq}

    # Fallback by form POST (JSON → http)
    @http.route(['/spw/attach_png_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png_http(self, **post):
        try:
            result = self.spw_attach_png()
            return request.make_json_response(result)
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    @http.route(['/spw/add_to_cart_meta_http'], type='http', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta_http(self, **post):
        try:
            result = self.spw_add_to_cart_meta()
            return request.make_json_response(result)
        except Exception as e:
            return request.make_json_response({'ok': False, 'message': str(e)})

    # ============================================
    # 3) Servir la previsualización por línea/índice
    # ============================================
    @http.route([
        '/spw/line_preview/<int:line_id>.png',
        '/spw/line_preview/<int:line_id>-<int:seq>.png',
        '/spw/line_preview/<int:line_id>',
    ], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview(self, line_id, seq=None, **kw):
        """Devuelve el PNG de la personalización 'seq' de esa línea.
        - Si viene ?i=<n> o path -<n> usa ese índice.
        - Si no hay índice, devuelve el último PNG; si no hay, 1x1 transparente.
        """
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        # índice vía query (?i=) si no vino en la ruta
        if seq is None:
            seq = _to_int(kw.get('i') or kw.get('idx'))

        Attachment = request.env['ir.attachment'].sudo()

        att = None
        if seq:
            # Busca exactamente el índice pedido
            att = Attachment.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', '=', 'image/png'),
                ('name', '=', f'spw_line_{line.id}_{int(seq)}.png'),
            ], limit=1)

        if not att:
            # Toma el más reciente nuestro
            att = Attachment.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', '=', 'image/png'),
                ('name', 'like', f'spw_line_{line.id}_%'),
            ], order='id desc', limit=1)

        if not att:
            # PNG transparente 1x1
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        headers = [
            ('Content-Type', 'image/png'),
            # Evitar cache agresivo para que se vea al instante
            ('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0'),
        ]
        return request.make_response(data, headers=headers)