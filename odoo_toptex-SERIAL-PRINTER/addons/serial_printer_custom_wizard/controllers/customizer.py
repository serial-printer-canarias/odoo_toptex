from odoo import http
from odoo.http import request
import base64


class SpwCustomizer(http.Controller):

    # Alias para mantener compatibilidad con rutas antiguas (/spw/customize)
    @http.route(['/spw/customizer', '/spw/customize'], type='http', auth='public', website=True, sitemap=False)
    def spw_customizer(self, product_id=None, variant_id=None, **kw):
        pt = request.env['product.template'].sudo().browse(int(product_id)) if product_id else None

        img_src = ''
        if variant_id:
            img_src = '/web/image/product.product/%s/image_1920' % int(variant_id)
        elif pt and pt.product_variant_id:
            img_src = '/web/image/product.product/%s/image_1920' % pt.product_variant_id.id

        values = {
            'template': pt,
            'variant_id': int(variant_id) if variant_id else False,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    @http.route('/spw/download_png', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def download_png(self, **post):
        b64 = (post.get('png_b64') or '').strip()
        if not b64:
            return request.not_found()
        raw = base64.b64decode(b64)
        headers = [
            ('Content-Type', 'image/png'),
            ('Content-Length', str(len(raw))),
            ('Content-Disposition', 'attachment; filename="personalizacion.png"'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
        ]
        return request.make_response(raw, headers=headers)
