# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
TAG = "[SPW][add_to_cart_meta]"

class SpwAddToCartMeta(http.Controller):
    """Crea SIEMPRE una línea nueva en el carrito para cada personalización.
    Evitamos _cart_update (que fusiona) y creamos la sale.order.line directamente
    con el precio de la tarifario del pedido.
    """

    # -------- JSON (fetch application/json) --------
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False)
    def add_to_cart_meta_json(self, variant_id, qty=1, tech='', svg_color='', notes='', spw_token=None, **kw):
        try:
            return self._create_line(int(variant_id or 0), float(qty or 1), tech, svg_color, notes, spw_token)
        except Exception as e:
            _logger.exception("%s JSON error: %s", TAG, e)
            return {'ok': False, 'message': 'No se pudo añadir (JSON).'}

    # -------- Fallback HTTP (form-data) --------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False)
    def add_to_cart_meta_http(self, **post):
        try:
            variant_id = int((post.get('variant_id') or '0').strip() or 0)
            qty = float(post.get('qty') or 1)
            tech = (post.get('tech') or '').strip()
            svg_color = (post.get('svg_color') or '').strip()
            notes = (post.get('notes') or '').strip()
            spw_token = (post.get('spw_token') or '').strip() or None
            res = self._create_line(variant_id, qty, tech, svg_color, notes, spw_token)
            return request.make_json_response(res)
        except Exception as e:
            _logger.exception("%s HTTP error: %s", TAG, e)
            return request.make_json_response({'ok': False, 'message': 'No se pudo añadir (HTTP).'})

    # ---------------- interno ----------------
    def _get_price(self, order, product, qty):
        """Obtiene precio unitario según tarifario del pedido (compatible)."""
        pricelist = order.pricelist_id
        partner = order.partner_id
        # Odoo 16/17/18: distintos nombres; probamos secuencialmente
        for attr in ('get_product_price', '_get_product_price', 'price_get'):
            fn = getattr(pricelist, attr, None)
            if callable(fn):
                try:
                    price = fn(product, qty, partner) if attr != 'price_get' else fn(product.id, qty, partner.id)[pricelist.id]
                    return float(price or 0.0)
                except Exception:
                    pass
        # Fallback básico: precio de lista público
        try:
            return float(product.lst_price or 0.0)
        except Exception:
            return 0.0

    def _create_line(self, variant_id, qty, tech, svg_color, notes, spw_token):
        if not variant_id:
            return {'ok': False, 'message': 'Falta la variante.'}

        env = request.env.sudo()
        product = env['product.product'].browse(variant_id)
        if not product.exists():
            return {'ok': False, 'message': 'La variante no existe.'}

        order = request.website.sale_get_order(force_create=True)
        if not order:
            return {'ok': False, 'message': 'No se pudo abrir el pedido.'}

        # Descripción SOLO de esta personalización (usada también por las píldoras)
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
            line_name += "\n" + " | ".join(extras)

        price_unit = self._get_price(order, product, qty)

        vals = {
            'order_id': order.id,
            'product_id': product.id,
            'name': line_name,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': price_unit,
        }

        _logger.info(
            "%s crear línea nueva -> order=%s product=%s qty=%s price=%s tech=%s color=%s token=%s",
            TAG, order.id, product.id, qty, price_unit, tech, svg_color, spw_token
        )

        line = env['sale.order.line'].create(vals)

        # Impuestos / fposición
        try:
            line._compute_tax_id()
        except Exception:
            pass

        _logger.info("%s línea creada OK -> line_id=%s", TAG, line.id)
        return {'ok': True, 'line_id': line.id, 'cart_url': '/shop/cart'}