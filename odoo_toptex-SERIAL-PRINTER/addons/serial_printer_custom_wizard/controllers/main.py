# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class SpwCustomizer(http.Controller):

    # ... tu ruta /spw/customize intacta ...

    @http.route('/spw/add_to_cart', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        # Siempre devolver JSON aunque sea type='http'
        def _json(payload, status=200):
            return request.make_json_response(payload, status=status)

        try:
            raw = request.httprequest.data or b''
            data = json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            return _json({'ok': False, 'message': 'JSON inválido.'}, status=400)

        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return _json({'ok': False, 'message': 'Parámetros inválidos.'}, status=400)

        if not variant_id or qty <= 0:
            return _json({'ok': False, 'message': 'Parámetros inválidos.'}, status=400)

        tech = data.get('tech') or ''
        svg_color = data.get('svg_color') or ''
        notes = data.get('notes') or ''
        png_b64 = data.get('png_b64') or ''

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return _json({'ok': False, 'message': 'Variante no encontrada.'}, status=404)

        # Crear/obtener pedido
        order = request.website.sale_get_order(force_create=True)

        # Usar el id devuelto por _cart_update (más fiable)
        res = order._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

        if line and line.exists():
            extras = []
            if tech:
                extras.append(f"Técnica: {tech}")
            if svg_color:
                extras.append(f"Color SVG: {svg_color}")
            if notes:
                extras.append(f"Obs: {notes}")
            if extras:
                base_name = line.name or variant.get_product_multiline_description_sale() or variant.display_name
                line.sudo().write({'name': base_name + "\n" + " | ".join(extras)})

            if png_b64:
                request.env['ir.attachment'].sudo().create({
                    'name': 'personalizacion.png',
                    'datas': png_b64,              # base64 sin prefijo
                    'type': 'binary',
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        return _json({'ok': True, 'cart_url': '/shop/cart'})