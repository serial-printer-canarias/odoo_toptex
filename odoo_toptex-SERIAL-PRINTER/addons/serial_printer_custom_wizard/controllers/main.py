# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class SpwCustomizer(http.Controller):

    # RUTA que acepta /spw/customize/4 y también /spw/customize?template_id=4
    @http.route(['/spw/customize/<int:template_id>', '/spw/customize'], 
                type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        # Aceptar querystring si viene así
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
            'variant_id': variant.id if variant.exists() else "",
            'img_src': img_src,
        }
        # IMPORTANTE: este ID debe existir en views/customizer_page.xml
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # Añadir al carrito (sin cambiar nada más del sistema)
    @http.route('/spw/add_to_cart', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        """ Recibe JSON y devuelve JSON siempre (aunque sea type='http'). """
        def _json(payload, status=200):
            return request.make_json_response(payload, status=status)

        try:
            raw = request.httprequest.data or b''
            data = json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            return _json({'ok': False, 'message': 'JSON inválido.'}, status=400)

        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return _json({'ok': False, 'message': 'Parámetros inválidos.'}, status=400)

        if not variant_id or qty <= 0:
            return _json({'ok': False, 'message': 'Parámetros inválidos.'}, status=400)

        tech = data.get('tech') or ''
        svg_color = data.get('svg_color') or ''
        notes = data.get('notes') or ''
        png_b64 = data.get('png_b64') or ''

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return _json({'ok': False, 'message': 'Variante no encontrada.'}, status=404)

        order = request.website.sale_get_order(force_create=True)

        # Más fiable: usar la línea devuelta por _cart_update
        res = order._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

        if line and line.exists():
            extras = []
            if tech:
                extras.append(f"Técnica: {tech}")
            if svg_color:
                extras.append(f"Color SVG: {svg_color}")
            if notes:
                extras.append(f"Obs: {notes}")
            if extras:
                base_name = line.name or variant.get_product_multiline_description_sale() or variant.display_name
                line.sudo().write({'name': base_name + "\n" + " | ".join(extras)})

            if png_b64:
                request.env['ir.attachment'].sudo().create({
                    'name': 'personalizacion.png',
                    'datas': png_b64,    # base64 sin prefijo
                    'type': 'binary',
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        return _json({'ok': True, 'cart_url': '/shop/cart'})