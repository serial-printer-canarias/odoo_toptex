# serial_printer_custom_wizard/controllers/main.py
from odoo import http
from odoo.http import request

class SPWController(http.Controller):

    @http.route("/spw/customize/<int:product_id>", type="http", auth="public", website=True, sitemap=False)
    def spw_customize(self, product_id, **kw):
        product = request.env["product.template"].sudo().browse(product_id)
        variant_id = int(kw.get("variant_id") or 0)

        if variant_id:
            variant = request.env["product.product"].sudo().browse(variant_id)
            if not variant.exists():
                variant = product.product_variant_id
        else:
            variant = product.product_variant_id

        values = {
            "product": product,
            "variant": variant,
        }
        return request.render("serial_printer_custom_wizard.customizer_page", values)