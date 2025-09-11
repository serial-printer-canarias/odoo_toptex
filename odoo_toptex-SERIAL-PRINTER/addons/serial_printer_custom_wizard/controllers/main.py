# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class SerialPrinterCustomizer(http.Controller):

    @http.route(['/personalizar/<int:product_id>'], type='http', auth='public', website=True, sitemap=False)
    def customizer(self, product_id, **kw):
        """Página de personalización. Soporta query ?vid=<variant_id>."""
        ProductTemplate = request.env['product.template'].sudo()
        ProductProduct = request.env['product.product'].sudo()

        tmpl = ProductTemplate.browse(product_id)
        if not tmpl.exists():
            # Si nos pasan un product.product por error
            variant_maybe = ProductProduct.browse(product_id)
            if variant_maybe.exists():
                tmpl = variant_maybe.product_tmpl_id
            else:
                return request.not_found()

        # Variante preferida: por querystring o primera disponible
        variant = None
        if kw.get('vid'):
            try:
                variant = ProductProduct.browse(int(kw['vid']))
                if not variant.exists():
                    variant = None
            except Exception:
                variant = None
        if not variant:
            variant = tmpl.product_variant_ids[:1]

        # Imagen base: prioriza la de la variante
        if variant:
            base_image_url = f"/web/image/product.product/{variant.id}/image_1920"
        else:
            base_image_url = f"/web/image/product.template/{tmpl.id}/image_1920"

        # Paleta (visual) tipo NS300 (ejemplo; amplía si quieres)
        ns_colors = [
            {"code": "000", "name": "Black",   "hex": "#000000"},
            {"code": "001", "name": "White",   "hex": "#FFFFFF"},
            {"code": "002", "name": "Navy",    "hex": "#001F3F"},
            {"code": "003", "name": "Royal",   "hex": "#2145FF"},
            {"code": "004", "name": "Red",     "hex": "#D81B24"},
            {"code": "005", "name": "Green",   "hex": "#1E7F33"},
            {"code": "006", "name": "Grey",    "hex": "#8A8A8A"},
            {"code": "007", "name": "Yellow",  "hex": "#FFCC00"},
        ]

        # >>>>>>>>> ÚNICO SITIO QUE PUEDES CAMBIAR (las técnicas) <<<<<<<<<
        techniques = ["Serigrafia", "DTF", "Bordado", "Marcado en cuero"]
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        # Título legible
        page_title = f"{tmpl.display_name} — Personalización"

        return request.render("serial_printer_custom_wizard.customizer_page", {
            "tmpl": tmpl,
            "variant": variant,
            "page_title": page_title,
            "base_image_url": base_image_url,
            "ns_colors_json": json.dumps(ns_colors),
            "techniques": techniques,
        })