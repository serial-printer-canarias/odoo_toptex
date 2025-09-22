# controllers/sp_matrix.py
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class SpMatrix(http.Controller):

    @http.route(
        "/sp/matrix/variants/<int:template_id>",
        type="http", auth="public", website=True, csrf=False
    )
    def sp_matrix_variants(self, template_id, **kw):
        """Devuelve mapping variante -> (product_id, imagen, precio, stock)
        en JSON plano (sin JSON-RPC, para poder usar fetch())."""
        tmpl = request.env["product.template"].sudo().browse(template_id)
        if not tmpl.exists():
            return request.make_response(
                json.dumps({"ok": False, "error": "template_not_found"}),
                headers=[("Content-Type", "application/json")],
            )

        # Mapa de combinación por conjunto de valores de atributo
        # key = "sorted(value_ids)". p.ej. "23-249"
        var_map = {}
        for p in tmpl.product_variant_ids.sudo():
            value_ids = p.product_template_attribute_value_ids.product_attribute_value_id.ids
            key = "-".join(str(i) for i in sorted(value_ids))
            var_map[key] = p

        # Detectar (opcional) cuáles son color/size
        color_attr = size_attr = None
        for line in tmpl.attribute_line_ids:
            n = (line.attribute_id.name or "").lower()
            if not color_attr and ("color" in n or "colour" in n):
                color_attr = line.attribute_id
            if not size_attr and (n in ("size", "talla", "talle", "taille") or "size" in n):
                size_attr = line.attribute_id

        # Listas de valores
        colors = request.env["product.attribute.value"]
        sizes = request.env["product.attribute.value"]
        if color_attr:
            colors = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == color_attr).value_ids
        if size_attr:
            sizes = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == size_attr).value_ids

        # Si no hay talla, tratamos como "One Size" con id -1
        size_ids = sizes.ids or [-1]

        records = []
        for c in (colors or request.env["product.attribute.value"]):
            for s in size_ids:
                comb = sorted([c.id] + ([] if s == -1 else [s]))
                key = "-".join(str(i) for i in comb)
                p = var_map.get(key)
                if not p:
                    continue
                # Imagen, precio y stock (usamos website context por simplicidad)
                img_url = f"/web/image/product.product/{p.id}/image_128"
                price = p.sudo().website_price
                qty = p.sudo().qty_available  # "On hand" como pediste
                records.append({
                    "color_id": c.id,
                    "size_id": s,
                    "product_id": p.id,
                    "image": img_url,
                    "price": price,
                    "qty_available": qty,
                })

        payload = {"ok": True, "template_id": tmpl.id, "records": records}
        return request.make_response(
            json.dumps(payload), headers=[("Content-Type", "application/json")]
        )

    @http.route(
        "/sp/matrix/add",
        type="http", auth="public", website=True, csrf=False, methods=["POST"]
    )
    def sp_matrix_add(self, **kw):
        """Añade varias líneas al carrito de una vez.
        Espera: {"lines":[{"product_id":123, "qty":2}, ...]}
        """
        try:
            data = json.loads(request.httprequest.data or b"{}")
        except Exception:
            data = {}
        lines = data.get("lines", []) or []
        order = request.website.sale_get_order(force_create=True)
        for line in lines:
            pid = int(line.get("product_id") or 0)
            qty = float(line.get("qty") or 0)
            if pid and qty > 0:
                # _cart_update maneja impuestos, pricelist, etc.
                order._cart_update(product_id=pid, add_qty=qty)
        return request.make_response(
            json.dumps({"ok": True, "cart_qty": order.cart_quantity}),
            headers=[("Content-Type", "application/json")],
        )