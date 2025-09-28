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

def _strip_data_url(b64_str):
    """Acepta 'data:image/png;base64,AAAA' o 'AAAA'. Devuelve solo la parte base64."""
    if not b64_str:
        return ''
    s = b64_str.strip()
    if ',' in s and ';base64' in s[:64]:
        return s.split(',', 1)[1]
    return s

class SpwCartController(http.Controller):

    # ====== 1) Crear/actualizar línea con metadatos (ACUMULA BLOQUES) ======
    @http.route(['/spw/add_to_cart_meta'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_add_to_cart_meta(self, **kw):
        """
        Crea/actualiza una línea en el carrito y AÑADE un bloque de texto por
        personalización (Técnica / Color SVG / Observaciones) al campo name.
        Devuelve {ok, line_id, cart_url}.
        """
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

        # _cart_update crea/actualiza línea (misma lógica estándar de website_sale)
        res = order._cart_update(product_id=product.id, add_qty=qty)
        line_id = res.get('line_id')
        if not line_id:
            return {'ok': False, 'message': _('Could not add line')}

        line = request.env['sale.order.line'].sudo().browse(line_id)

        # Guardar metadatos "últimos" (compatibilidad con tus campos)
        write_vals = {
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        }
        try:
            line.sudo().write(write_vals)
        except Exception:
            # Si algún campo no existe en el entorno, seguimos sin romper
            pass

        # ---- ACUMULAR BLOQUE DE TEXTO (uno por personalización) ----
        block_parts = []
        if tech:
            block_parts.append(f"Técnica: {tech}")
        if svg_color:
            block_parts.append(f"Color SVG: {svg_color}")
        if notes:
            block_parts.append(f"Observaciones: {notes}")

        if block_parts:
            block = " | ".join(block_parts)
            base = (line.name or '').strip()
            # Evitar duplicados exactos
            if block not in base.splitlines():
                new_name = (base + ("\n" if base else "") + block).strip()
                line.sudo().write({'name': new_name})

        return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}

    # ====== 2) Adjuntar PNG (NO sobrescribe anteriores; acumula) ======
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """
        Crea un adjunto PNG para la línea. No borra los anteriores.
        Mantiene compatibilidad dejando el último en spw_png_attachment_id si existe.
        """
        data = request.jsonrequest or {}
        line_id = _to_int(data.get('line_id'))
        png_b64 = _strip_data_url(data.get('png_b64'))

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
            'datas': png_b64,  # base64 sin encabezado
        }
        att = request.env['ir.attachment'].sudo().create(att_vals)

        # Compatibilidad: guardar el último en el M2O si el campo existe
        try:
            line.sudo().write({'spw_png_attachment_id': att.id})
        except Exception:
            pass

        return {'ok': True, 'attachment_id': att.id}

    # ====== 2b) Fallbacks HTTP por si el fetch JSON falla ======
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

    # ====== 3) Servir la previsualización: soporta ?i=n (1..n) ======
    @http.route(['/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview(self, line_id, **kw):
        """
        Devuelve la imagen de previsualización de la línea.
        Soporta el parámetro de query ?i=1..n para múltiples personalizaciones,
        ordenando los adjuntos por create_date asc.
        """
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        i = _to_int(request.httprequest.args.get('i'), 1)
        if i <= 0:
            i = 1

        Att = request.env['ir.attachment'].sudo()
        atts = Att.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('mimetype', '=', 'image/png'),
            ('name', 'like', 'spw_line_%'),
        ], order='create_date asc')

        att = False
        if atts and len(atts) >= i:
            att = atts[i - 1]
        elif line.sudo().exists() and getattr(line, 'spw_png_attachment_id', False):
            att = line.sudo().spw_png_attachment_id

        if not att:
            # PNG transparente 1x1 para no romper maquetación
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])