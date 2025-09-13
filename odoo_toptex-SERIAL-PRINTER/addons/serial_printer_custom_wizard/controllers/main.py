# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class SerialPrinterWizard(http.Controller):

    @http.route(['/spw/customize/<int:variant_id>'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, variant_id, **kw):
        """Página del configurador.
        - Evita el TypeError del editor pasando main_object correctamente.
        - Muestra la imagen de la variante seleccionada.
        """
        ProductProduct = request.env['product.product'].sudo()
        variant = ProductProduct.browse(variant_id)
        if not variant.exists():
            return request.not_found()

        # URL de imagen de la variante (route estándar /web/image)
        product_image_url = f"/web/image/product.product/{variant.id}/image_1920"

        # FIX: el editor de Website necesita main_object (un record real con modelo)
        main_object = variant.product_tmpl_id  # product.template

        qcontext = {
            'variant_id': variant.id,
            'product_image_url': product_image_url,
            'main_object': main_object,
        }
        return request.render('serial_printer_custom_wizard.customizer_page', qcontext)