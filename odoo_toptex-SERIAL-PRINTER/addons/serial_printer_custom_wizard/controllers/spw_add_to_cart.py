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


def _count_blocks(name_text: str) -> int:
    """Cuenta bloques '— Personalización N —' en el name de la línea."""
    if not name_text:
        return 0
    return len(re.findall(r'—\s*Personalización\s*\d+\s*—', name_text))


class SpwCartController(http.Controller):
    # =========================================================
    # 1) Crear/actualizar línea y añadir BLOQUE de personalización
    # =========================================================
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        """
        Crea/actualiza la línea y AÑADE un bloque nuevo al 'name' con:
        — Personalización N — / Técnica / Color SVG / Observaciones

        Devuelve line_id, seq (N) y la URL del carrito.
        """
        vals = request.jsonrequest or {}
        variant_id = _to_int(vals.get('variant_id'))
        qty        = _to_int(vals.get('qty', 1), 1)
        tech       = (vals.get('tech') or '').strip()
        svg_color  = (vals.get('svg_color') or '').strip()
        notes      = (vals.get('notes') or '').strip()

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': _('Bad payload')}

        # Pedido y producto
        order = request.website.sale_get_order(force_create=True)
        product = request.env['product.product'].sudo().browse(variant_id).exists()
        if not product:
            return {'ok': False, 'message': _('Product not found')}

        # _cart_update: puede reutilizar la línea del mismo SKU (está bien)
        res = order._cart_update(product_id=product.id, add_qty=qty)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Siguiente índice N (cuenta bloques ya presentes)
        current_name = (line.name or '').strip()
        next_seq = _count_blocks(current_name) + 1

        # Construir bloque nuevo
        block_lines = [f"— Personalización {next_seq} —"]
        if tech:
            block_lines.append(f"Técnica: {tech}")
        if svg_color:
            block_lines.append(f"Color SVG: {svg_color}")
        if notes:
            block_lines.append(f"Observaciones: {notes}")

        new_name = (current_name + ("\n" if current_name else "") + "\n".join(block_lines)).strip()
        line.sudo().write({
            'name': new_name,
            # Guardamos también metadatos "últimos" por si se usan en informes
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        })

        return {
            'ok': True,
            'line_id': line.id,
            'seq': next_seq,
            'cart_url': '/shop/cart',
            'preview_url': f'/spw/line_preview/{line.id}-{next_seq}.png',
        }

    # =========================================================
    # 2) Adjuntar PNG de una personalización concreta (seq)
    # =========================================================
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """
        Adjunta un PNG (base64) para la línea y el índice 'seq' indicado.
        Si no se pasa seq, usa el siguiente disponible.
        """
        data = request.jsonrequest or {}
        line_id = _to_int(data.get('line_id'))
        png_b64 = (data.get('png_b64') or '').strip()
        seq     = _to_int(data.get('seq'), 0)

        if not line_id or not png_b64:
            return {'ok': False, 'message': _('Missing data')}

        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return {'ok': False, 'message': _('Line not found')}

        # Si no viene seq, calculamos el siguiente según adjuntos existentes
        Att = request.env['ir.attachment'].sudo()
        pattern = f"spw_line_{line.id}_"
        existing = Att.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('mimetype', '=', 'image/png'),
            ('name', 'ilike', pattern + '%'),
        ])
        if not seq:
            # siguiente libre = max + 1
            max_seq = 0
            for att in existing:
                m = re.search(rf"spw_line_{line.id}_(\d+)\.png$", att.name or '')
                if m:
                    max_seq = max(max_seq, int(m.group(1)))
            seq = max_seq + 1

        # Si ya existía el de ese seq, lo sustituimos
        for att in existing:
            if re.fullmatch(rf"spw_line_{line.id}_{seq}\.png", att.name or ''):
                att.unlink()
                break

        att_name = f"spw_line_{line.id}_{seq}.png"
        att_vals = {
            'name': att_name,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'mimetype': 'image/png',
            'datas': png_b64,  # ya viene base64
        }
        att = Att.create(att_vals)

        # Many2one opcional (conserva el último subido)
        line.sudo().write({'spw_png_attachment_id': att.id})

        return {'ok': True, 'attachment_id': att.id, 'seq': seq}

    # Fallbacks HTTP (por si fetch JSON falla en algún navegador)
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

    # =========================================================
    # 3) Servir previsualizaciones por índice
    # =========================================================
    @http.route(['/spw/line_preview/<int:line_id>-<int:seq>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview_seq(self, line_id, seq, **kw):
        """Devuelve el PNG de la línea + índice. 1x1 si no existe."""
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        name = f"spw_line_{line.id}_{seq}.png"
        att = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('mimetype', '=', 'image/png'),
            ('name', '=', name),
        ], limit=1)

        if not att:
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])

    # Compatibilidad: si piden sin índice, devolvemos la #1
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview_legacy(self, line_id, **kw):
        return self.spw_line_preview_seq(line_id, 1, **kw)