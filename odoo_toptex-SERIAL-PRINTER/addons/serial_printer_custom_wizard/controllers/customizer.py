# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64

class SPWCustomizer(http.Controller):

    @http.route(['/spw/customizer'], type='http', auth='public', website=True, methods=['GET'])
    def spw_customizer(self, **kw):
        pid = int(kw.get('product_id') or 0)
        vid = int(kw.get('variant_id') or 0)

        PT = request.env['product.template'].sudo()
        PP = request.env['product.product'].sudo()

        template = PT.browse(pid) if pid else None
        variant = PP.browse(vid) if vid else None

        if not template and variant:
            template = variant.product_tmpl_id
        if not variant and template:
            variant = template.product_variant_id

        img_src = ''
        if variant and variant.id:
            img_src = '/web/image/product.product/%s/image_1920' % variant.id
        elif template and template.id:
            img_src = '/web/image/product.template/%s/image_1920' % template.id

        values = {
            'template': template,
            'variant_id': variant.id if variant else 0,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # Descarga segura por POST (evita bloqueos de data:)
    @http.route(['/spw/download_png'], type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def spw_download_png(self, **post):
        png_b64 = (post.get('png_b64') or '').strip()
        data = base64.b64decode(png_b64) if png_b64 else b''
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', 'attachment; filename="personalizacion.png"'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate'),
        ]
        return request.make_response(data, headers=headers)