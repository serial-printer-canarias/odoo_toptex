# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SPW_LOG_TAG = "[SPW][add_to_cart]"

class SpwAddToCartMeta(http.Controller):

    # --- JSON (fetch con application/json) ---
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta_json(self, variant_id, qty=1, tech='', svg_color='', notes='', spw_token=None, **kw):
        try:
            return self._do_add(int(variant_id or 0), qty, tech, svg_color, notes, spw_token)
        except Exception as e:
            _logger.exception("%s JSON error: %s", SPW_LOG_TAG, e)
            return {'ok': False, 'message': 'Error inesperado (JSON).'}

    # --- Fallback FORM (Content-Type: multipart/form-data) ---
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        try:
            variant_id = int((post.get('variant_id') or '0').strip() or 0)
            qty = float(post.get('qty') or 1)
            tech = (post.get('tech') or '').strip()
            svg_color = (post.get('svg_color') or '').strip()
            notes = (post.get('notes') or '').strip()
            spw_token = (post.get('spw_token') or '').strip() or None
            res = self._do_add(variant_id, qty, tech, svg_color, notes, spw_token)
            return request.make_json_response(res)
        except Exception as e:
            _logger.exception("%s HTTP error: %s", SPW_LOG_TAG, e)
            return request.make_json_response({'ok': False, 'message': 'Error inesperado (HTTP).'})

    # ---------------- interno ----------------
    def _do_add(self, variant_id, qty, tech, svg_color, notes, spw_token):
        if not variant_id:
            return {'ok': False, 'message': 'Falta la variante.'}

        sudo_env = request.env.sudo()
        product = sudo_env['product.product'].browse(int(variant_id))
        if not product.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        order = request.website.sale_get_order(force_create=True)
        if not order:
            return {'ok': False, 'message': 'No se pudo abrir el pedido.'}

        # Texto de personalización SOLO de este click
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

        # LOG de entrada
        _logger.info(
            "%s try add: order=%s product=%s qty=%s tech=%s color=%s token=%s",
            SPW_LOG_TAG, order.id, product.id, qty, tech, svg_color, spw_token
        )

        # Fuerza CREAR línea nueva (no fusiona con otras de mismo SKU)
        try:
            res = order._cart_update(
                product_id=product.id,
                add_qty=float(qty or 1),
                set_qty=None,
                line_id=None,
                force_create=True,  # CLAVE para separar personalizaciones
            )
        except TypeError:
            # Por si la firma del método difiere según build, reintento sin named args “extraños”
            res = order._cart_update(product_id=product.id, add_qty=float(qty or 1), set_qty=None)

        line_id = int(res.get('line_id') or res.get('line') or 0)
        if not line_id:
            _logger.warning("%s no line_id in result: %s", SPW_LOG_TAG, res)
            return {'ok': False, 'message': 'No se pudo crear la línea.'}

        line = sudo_env['sale.order.line'].browse(line_id)
        if not line.exists():
            _logger.warning("%s line %s not exists after _cart_update", SPW_LOG_TAG, line_id)
            return {'ok': False, 'message': 'Línea no disponible.'}

        # Escribir solo la personalización actual en el nombre
        try:
            line.write({'name': line_name})
            try:
                line._compute_tax_id()
            except Exception:
                pass
        except Exception as e:
            _logger.exception("%s write name failed line=%s: %s", SPW_LOG_TAG, line_id, e)

        _logger.info(
            "%s added OK: order=%s line=%s name_len=%s",
            SPW_LOG_TAG, order.id, line.id, len(line_name or '')
        )
        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}