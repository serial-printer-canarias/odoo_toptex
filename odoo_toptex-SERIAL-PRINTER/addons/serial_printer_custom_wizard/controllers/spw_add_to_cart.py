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

        # Guarda metadatos "últimos" en campos simples (no listas)
        line_vals = {
            'spw_tech': tech or False,
            'spw_svg_color': svg_color or False,
            'spw_notes': notes or False,
        }
        line.sudo().write(line_vals)

        # Asegurar que la descripción visible incluya Técnica/Color como histórico (una línea por personalización)
        # No duplicamos si ya existe la pareja exacta.
        base_name = (line.name or '').strip()
        tech_line  = f"Técnica: {tech}" if tech else ""
        color_line = f"Color SVG: {svg_color}" if svg_color else ""
        block = "\n".join([s for s in [tech_line, color_line] if s])
        if block and block not in base_name:
            new_name = (base_name + ("\n" if base_name else "") + block).strip()
            line.sudo().write({'name': new_name})

        return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}

    # ====== 2) Adjuntar PNG a la línea (acumulando) ======
    @http.route(['/spw/attach_png'], type='json', auth='public', methods=['POST'], csrf=False)
    def spw_attach_png(self, **kw):
        """Adjunta un PNG (en base64) a la línea del carrito y guarda la
        referencia más reciente en spw_png_attachment_id. NO borra anteriores."""
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
        # guardamos el último para compatibilidad
        line.sudo().write({'spw_png_attachment_id': att.id})
        return {'ok': True, 'attachment_id': att.id}

    # Fallback por POST clásico (si el fetch JSON no funciona)
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

    # ====== 3) PREVIEWs: i-ésimo PNG y JSON con todas las personalizaciones ======

    def _attachments_for_line(self, line):
        return request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('mimetype', '=', 'image/png'),
            ('name', 'ilike', 'spw_line_%'),
        ], order='id ASC')

    def _parse_blocks_from_name(self, name_text):
        """Devuelve listas indexadas de técnicas y colores encontradas en line.name."""
        txt = name_text or ''
        techs  = re.findall(r'Técnica\s*:\s*([^\n\r]+)', txt)
        colors = re.findall(r'Color\s*SVG\s*:\s*(#[0-9a-fA-F]{3,8})', txt)
        return techs, colors

    @http.route(['/spw/line_preview/<int:line_id>/<int:i>.png',
                 '/spw/line_preview/<int:line_id>.png'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_preview(self, line_id, i=1, **kw):
        """Devuelve el PNG N (1-indexado) de la línea; si no hay, imagen 1x1."""
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.not_found()

        atts = self._attachments_for_line(line)
        att = atts[i-1] if (i and i-1 < len(atts)) else (line.sudo().spw_png_attachment_id or (atts[:1] and atts[:1][0]))
        if not att:
            tiny = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAEklEQVR42mP8/5+hHgAHggJ/2k7O6wAAAABJRU5ErkJggg==")
            return request.make_response(tiny, headers=[('Content-Type', 'image/png')])

        data = b64decode(att.datas)
        return request.make_response(data, headers=[('Content-Type', 'image/png')])

    @http.route(['/spw/line_personalizations/<int:line_id>'], type='http', auth='public', methods=['GET'], csrf=False)
    def spw_line_personalizations(self, line_id, **kw):
        """JSON con [{img, color, tech}] para pintar en el carrito en vertical."""
        line = request.env['sale.order.line'].sudo().browse(line_id).exists()
        if not line:
            return request.make_json_response({'ok': False, 'items': []})

        atts  = self._attachments_for_line(line)
        techs, colors = self._parse_blocks_from_name(line.name or "")

        n = max(len(atts), len(techs), len(colors), 1)
        items = []
        ts = int(time.time())
        for idx in range(n):
            img_url = '/spw/line_preview/%d/%d.png?v=%d' % (line.id, idx+1, ts)
            tech = (techs[idx] if idx < len(techs) else (techs[-1] if techs else "")) or ""
            col  = (colors[idx] if idx < len(colors) else (colors[-1] if colors else "")) or ""
            items.append({'img': img_url, 'tech': tech, 'color': col})

        return request.make_json_response({'ok': True, 'items': items})