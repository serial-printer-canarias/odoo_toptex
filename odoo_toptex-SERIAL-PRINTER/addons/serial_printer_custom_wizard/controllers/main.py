# addons/serial_printer_custom_wizard/controllers/main.py
from odoo import http
from odoo.http import request

class SPWCustomizeController(http.Controller):

    @http.route(['/personalizar/<int:product_tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def customize(self, product_tmpl_id, variant_id=None, **kw):
        """Página de personalización.
        product_tmpl_id -> product.template.id
        variant_id (opcional) -> product.product.id
        """
        ProductTemplate = request.env['product.template'].sudo()
        ProductProduct = request.env['product.product'].sudo()

        product = ProductTemplate.browse(product_tmpl_id)
        if not product.exists():
            return request.not_found()

        variant = None
        if variant_id:
            v = ProductProduct.browse(int(variant_id))
            if v.exists() and v.product_tmpl_id.id == product.id:
                variant = v

        # Fallback: primera combinación posible si no se pasa variant_id
        if not variant:
            variant = product._get_first_possible_variant()

        values = {
            'product': product,
            'variant': variant,
        }
        # ****** IMPORTANTE ******
        # Renderizar el XML-ID correcto del template:
        return request.render("serial_printer_custom_wizard.spw_customize_page", values)