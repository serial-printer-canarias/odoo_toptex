# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwAddToCartMeta(http.Controller):

    # JSON
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta_json(self, variant_id, qty=1, tech='', svg_color='', notes='', spw_token=None, **kw):
        return self._do_add(int(variant_id), qty, tech, svg_color, notes, spw_token)

    # FORM fallback
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        try:
            variant_id = int(post.get('variant_id') or 0)
        except Exception:
            variant_id = 0
        qty = float(post.get('qty') or 1)
        tech = (post.get('tech') or '').strip()
        svg_color = (post.get('svg_color') or '').strip()
        notes = (post.get('notes') or '').strip()
        spw_token = (post.get('spw_token') or '').strip() or None
        res = self._do_add(variant_id, qty, tech, svg_color, notes, spw_token)
        return request.make_json_response(res)

    # ---------------- internal ----------------
    def _do_add(self, variant_id, qty, tech, svg_color, notes, spw_token):
        if not variant_id:
            return {'ok': False, 'message': 'Falta la variante.'}

        product = request.env['product.product'].sudo().browse(int(variant_id))
        if not product.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        order = request.website.sale_get_order(force_create=True)

        # Texto claro de la personalización (una sola vez por línea)
        extras = []
        if tech:
            extras.append(f"Técnica: {tech}")
        if svg_color:
            extras.append(f"Color SVG: {svg_color}")
        if notes:
            extras.append(f"Notas: {notes}")
        if spw_token:
            extras.append(f"Ref: {spw_token}")

        line_name = product.display_name
        if extras:
            line_name = f"{line_name}\n" + " | ".join(extras)

        # Fuerza línea nueva SIEMPRE (no fusiona con otras)
        # Odoo 18: _cart_update acepta force_create
        res = order._cart_update(
            product_id=product.id,
            add_qty=float(qty or 1),
            set_qty=None,
            line_id=None,
            force_create=True,   # << clave para no fusionar
        )

        line_id = res.get('line_id') or res.get('line') or False
        if not line_id:
            return {'ok': False, 'message': 'No se pudo crear la línea.'}

        line = request.env['sale.order.line'].sudo().browse(int(line_id))
        if line.exists():
            # Escribimos el name con esta personalización (sin arrastrar anteriores)
            line.write({'name': line_name})
            # Asegurar impuestos recalculados
            try:
                line._compute_tax_id()
            except Exception:
                pass

        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}