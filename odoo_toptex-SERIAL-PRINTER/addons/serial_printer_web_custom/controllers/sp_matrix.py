# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request

class SpMatrix(http.Controller):

    @http.route('/sp_matrix/v1/variants', type='http', auth='public', website=True, csrf=False)
    def variants(self, **kw):
        """Devuelve imágenes por color y combos (product_id, price, stock) por color/talla."""
        variant_id = int(request.params.get('variant_id') or 0)
        variant = request.env['product.product'].sudo().browse(variant_id)
        if not variant.exists():
            return request.make_response(json.dumps({}), headers=[('Content-Type','application/json')])

        tmpl = variant.product_tmpl_id

        # detectar líneas color/talla
        color_line = False
        size_line = False
        for line in tmpl.attribute_line_ids:
            name = (line.attribute_id.name or '').lower()
            if not color_line and ('color' in name or 'colour' in name):
                color_line = line
            if not size_line and (name in ('size','talla','talle','taille','größe','maat') or 'talla' in name):
                size_line = line

        color_values = color_line.value_ids if color_line else request.env['product.attribute.value'].sudo()
        size_values = size_line.value_ids if size_line else request.env['product.attribute.value'].sudo()

        pp = request.env['product.product'].sudo().search([('product_tmpl_id','=',tmpl.id)])
        var_map = []
        for p in pp:
            avs = set(p.product_template_attribute_value_ids.mapped('product_attribute_value_id').ids)
            var_map.append((p, avs))

        images = {}
        for cv in color_values:
            prod = next((p for (p,avs) in var_map if cv.id in avs), False)
            if prod:
                images[str(cv.id)] = f"/web/image/product.product/{prod.id}/image_128"
            else:
                images[str(cv.id)] = f"/web/image/product.template/{tmpl.id}/image_128"

        combos = {}
        size_ids = size_values.ids or [0]  # 0 = sin talla (una columna)
        for c in (color_values.ids or []):
            for s in size_ids:
                prod = False
                for p, avs in var_map:
                    if c in avs and (s == 0 or s in avs):
                        prod = p
                        break
                if prod:
                    price = float(prod.lst_price)
                    stock = float(getattr(prod, 'qty_available', 0.0))
                    combos[f"{c}-{s}"] = {"product_id": prod.id, "price": price, "stock": stock}

        payload = {"template_id": tmpl.id, "images": images, "combos": combos}
        return request.make_response(json.dumps(payload), headers=[('Content-Type','application/json')])

    @http.route('/sp_matrix/v1/add', type='http', auth='public', website=True, csrf=False)
    def add(self, **kw):
        """Añade múltiples líneas al carrito: body JSON -> {lines:[{product_id:int, qty:number}, ...]}"""
        body = request.jsonrequest or {}
        lines = body.get('lines') or []
        order = request.website.sale_get_order(force_create=True)
        for l in lines:
            pid = int(l.get('product_id', 0))
            qty = float(l.get('qty', 0))
            if pid and qty:
                order._cart_update(product_id=pid, add_qty=qty)
        return request.make_response(json.dumps({"ok": True, "order_id": order.id}),
                                     headers=[('Content-Type','application/json')])