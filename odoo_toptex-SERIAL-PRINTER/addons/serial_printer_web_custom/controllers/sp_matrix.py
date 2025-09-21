# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SPMatrix(http.Controller):

    @http.route('/sp/combination', type='json', auth='public', cors='*')
    def sp_combination(self, template_id=None, ptav_ids=None, qty=1.0):
        """Devuelve variante, precio, stock e imagen para una combinación de valores de atributo."""
        try:
            if not template_id or not ptav_ids:
                return {"ok": False, "error": "missing-params"}

            template = request.env["product.template"].sudo().browse(int(template_id))
            if not template.exists():
                return {"ok": False, "error": "template-not-found"}

            need = set(int(v) for v in ptav_ids)
            product = False
            for p in template.sudo().product_variant_ids:
                got = set(p.product_template_attribute_value_ids.ids)
                if need.issubset(got):
                    product = p
                    break
            if not product:
                # último recurso: primera variante
                product = template.sudo().product_variant_ids[:1]

            if not product:
                return {"ok": False, "error": "product-not-found"}

            # Precio por tarifa del website si existe; si no, lst_price
            pricelist = getattr(request, "website", False) and request.website.get_current_pricelist() or False
            partner = request.env.user.sudo().partner_id
            price = product.sudo().lst_price
            try:
                if pricelist:
                    price_ctx = product.sudo().with_context(
                        partner=partner.id,
                        quantity=float(qty or 1.0),
                        pricelist=pricelist.id,
                    )
                    # _get_product_price es estable en website_sale (Odoo 15-18)
                    price = pricelist.sudo()._get_product_price(product, float(qty or 1.0), partner=partner) or price
            except Exception:
                pass

            stock = product.sudo().qty_available  # usa free_qty si lo prefieres
            image = f"/web/image/product.product/{product.id}/image_128"

            return {
                "ok": True,
                "product_id": product.id,
                "price": price,
                "stock": stock,
                "image": image,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @http.route('/sp/product_info/<int:product_id>', type='json', auth='public', cors='*')
    def sp_product_info(self, product_id, qty=1.0):
        """Info directa por product_id (fallback público)."""
        try:
            product = request.env["product.product"].sudo().browse(int(product_id))
            if not product.exists():
                return {"ok": False, "error": "product-not-found"}

            pricelist = getattr(request, "website", False) and request.website.get_current_pricelist() or False
            partner = request.env.user.sudo().partner_id
            price = product.sudo().lst_price
            try:
                if pricelist:
                    price = pricelist.sudo()._get_product_price(product, float(qty or 1.0), partner=partner) or price
            except Exception:
                pass

            stock = product.sudo().qty_available
            image = f"/web/image/product.product/{product.id}/image_128"

            return {
                "ok": True,
                "product_id": product.id,
                "price": price,
                "stock": stock,
                "image": image,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}