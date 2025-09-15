# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
from werkzeug.wrappers import Response

class SpwCustomizer(http.Controller):

    # Página de personalización (soporta /spw/customize y /spw/customize/<id>)
    @http.route(['/spw/customize/<int:template_id>', '/spw/customize'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        # Compatibilidad con querystring
        if template_id is None:
            tid = kw.get('template_id') or request.params.get('template_id')
            template_id = int(tid) if tid else None
        vid = variant_id or kw.get('variant_id') or request.params.get('variant_id')
        variant_id = int(vid) if vid else None

        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        template = ProductTmpl.browse(template_id) if template_id else ProductTmpl.browse()
        variant = Product.browse(variant_id) if variant_id else Product.browse()

        img_src = ""
        if variant and variant.exists():
            img_src = f"/web/image/product.product/{variant.id}/image_1920"
        elif template and template.exists():
            img_src = f"/web/image/product.template/{template.id}/image_1920"

        values = {
            'template': template if template.exists() else False,
            'variant_id': variant.id if (variant and variant.exists()) else "",
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # ====== CARRITO: PRIMERA LLAMADA (crea línea y guarda metadatos) ======
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart_meta(self, **kw):
        data = request.jsonrequest or {}
        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        tech = (data.get('tech') or '').strip()
        svg_color