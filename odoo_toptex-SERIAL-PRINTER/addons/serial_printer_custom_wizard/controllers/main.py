# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request


class SPWCustomizer(http.Controller):

    @http.route(
        "/spw/customize/<int:tmpl_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def spw_customize(self, tmpl_id, variant_id=None, **kw):
        ProductT = request.env["product.template"].sudo()
        Variant = request.env["product.product"].sudo()

        product_template = ProductT.browse(tmpl_id).exists()
        variant = None
        if variant_id:
            v = Variant.browse(int(variant_id)).exists()
            if v and v.product_tmpl_id.id == tmpl_id:
                variant = v

        values = {
            "product_template": product_template,
            "variant": variant,
        }
        return request.render(
            "serial_printer_custom_wizard.spw_customizer_page", values
        )

    @http.route(
        "/spw/add_to_cart",
        type="http",
        auth="public",
        website=True,
        methods=["POST"],
        csrf=False,
    )
    def spw_add_to_cart(self, **post):
        """Añade al carro con personalización + guarda adjunto y parámetros."""
        Variant = request.env["product.product"].sudo()
        variant_id = int(post.get("variant_id") or 0)
        tmpl_id = int(post.get("tmpl_id") or 0)

        # Localiza variante (si no vino, coge la 1ª disponible del template)
        variant = None
        if variant_id:
            variant = Variant.browse(variant_id).exists()
        if not variant and tmpl_id:
            variant = Variant.search(
                [("product_tmpl_id", "=", tmpl_id), ("active", "=", True)], limit=1
            )

        if not variant:
            return request.redirect("/shop")

        # Añadir al carrito (1 uds)
        order = request.website.sale_get_order(force_create=True)
        update = order._cart_update(product_id=variant.id, add_qty=1)
        line = request.env["sale.order.line"].sudo().browse(update.get("line_id"))

        # Parámetros del customizer
        params = {
            "size": post.get("spw_size") or "",
            "rotation": post.get("spw_rotation") or "",
            "pos_x": post.get("spw_pos_x") or "",
            "pos_y": post.get("spw_pos_y") or "",
            "color": post.get("spw_color") or "",
            "ptype": post.get("spw_ptype") or "",
        }

        # Adjuntar logo si llegó
        logo = request.httprequest.files.get("logo_file")
        if logo:
            raw = logo.read()
            request.env["ir.attachment"].sudo().create({
                "name": logo.filename,
                "datas": base64.b64encode(raw),
                "res_model": "sale.order.line",
                "res_id": line.id,
                "mimetype": logo.mimetype,
            })
            params["logo_name"] = logo.filename

        # Añadir los parámetros al nombre de línea (no rompe nada)
        nice = (
            f"\n[PERSONALIZACIÓN] tipo={params['ptype'] or '-'} | "
            f"color={params['color'] or '-'} | "
            f"tam={params['size'] or '-'} | rot={params['rotation'] or '-'} | "
            f"x={params['pos_x'] or '-'} | y={params['pos_y'] or '-'}"
            f"{' | logo=' + params['logo_name'] if params.get('logo_name') else ''}"
        )
        line.name = (line.name or "") + nice

        return request.redirect("/shop/cart")