# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

def _norm(s):
    return (s or "").strip().lower()

class SpMatrix(http.Controller):

    @http.route("/sp_matrix/map", type="json", auth="public", website=True, csrf=False)
    def sp_matrix_map(self, pt_id=None, **kw):
        """Devuelve la tabla de combinaciones de un product.template:
        - colores (con miniatura)
        - tallas ordenadas
        - matriz color-talla -> {product_id, price, stock, image}
        """
        try:
            pt_id = int(pt_id or 0)
        except Exception:
            pt_id = 0

        pt = request.env["product.template"].sudo().browse(pt_id)
        if not pt or not pt.exists():
            return {"ok": False, "error": "template_not_found"}

        # Detectar atributos color/talla por nombre
        color_attr = size_attr = None
        for line in pt.attribute_line_ids:
            name = _norm(line.attribute_id.name)
            if not color_attr and any(k in name for k in ["color", "colour"]):
                color_attr = line.attribute_id
            if not size_attr and any(k in name for k in ["talla","size","taille","talle","maat","größe"]):
                size_attr = line.attribute_id

        def size_sort_key(v):
            s = (v.name or "").upper()
            # Primero numéricas (6, 8, 10, ...)
            num = "".join(ch for ch in s if ch.isdigit())
            if num:
                try:
                    return (0, float(num))
                except Exception:
                    pass
            # Después estándar
            std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"]
            return (1, std.index(s) if s in std else 999, s)

        colors, sizes = [], []

        if color_attr:
            line = pt.attribute_line_ids.filtered(lambda l: l.attribute_id.id == color_attr.id)
            for v in line.value_ids:
                colors.append({"id": v.id, "name": v.name})

        if size_attr:
            line = pt.attribute_line_ids.filtered(lambda l: l.attribute_id.id == size_attr.id)
            for v in sorted(line.value_ids, key=size_sort_key):
                sizes.append({"id": v.id, "name": v.name})

        # Indexar variantes por (color, talla)
        def _img_for(prod):
            if getattr(prod, "image_128", False):
                return f"/web/image/product.product/{prod.id}/image_128"
            return f"/web/image/product.template/{pt.id}/image_128"

        by_key = {}
        variants = pt.product_variant_ids.sudo()
        # Pricelist actual si existe pedido
        order = request.website.sale_get_order(force_create=False)
        pricelist = (order.pricelist_id if order else request.website.get_current_pricelist())

        for p in variants:
            pavs = p.product_template_attribute_value_ids.mapped("product_attribute_value_id")
            c_id = s_id = 0
            for v in pavs:
                if color_attr and v.attribute_id.id == color_attr.id:
                    c_id = v.id
                if size_attr and v.attribute_id.id == size_attr.id:
                    s_id = v.id
            key = f"{c_id}-{s_id}"
            # Precio simple (pricelist). Evitamos cálculos complejos para estabilidad.
            price = p.with_context(pricelist=pricelist.id).price if hasattr(p, "price") else p.lst_price
            stock = getattr(p, "qty_available", 0.0)
            by_key[key] = {
                "product_id": p.id,
                "price": float(price or 0.0),
                "stock": float(stock or 0.0),
                "image": _img_for(p),
            }

        # Elegir miniatura por color (primera variante encontrada con ese color)
        color_imgs = {}
        for c in colors:
            # preferir variante específica
            found = None
            for k, data in by_key.items():
                cid, _sid = (int(x) for x in k.split("-"))
                if cid == c["id"]:
                    found = data["image"]
                    break
            color_imgs[c["id"]] = found or f"/web/image/product.template/{pt.id}/image_128"

        # Adjuntar imagen a cada color
        for c in colors:
            c["image"] = color_imgs.get(c["id"])

        return {
            "ok": True,
            "template_id": pt.id,
            "colors": colors,
            "sizes": sizes,
            "matrix": by_key,  # dict: "colorId-sizeId" -> {product_id, price, stock, image}
        }