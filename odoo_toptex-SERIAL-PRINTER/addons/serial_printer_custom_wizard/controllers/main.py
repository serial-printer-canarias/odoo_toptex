# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json

class SpwCustomizer(http.Controller):

    # Página de personalización (acepta /spw/customize/<id> y querystring)
    @http.route(['/spw/customize/<int:template_id>', '/spw/customize'], type='http',
                auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id=None, variant_id=None, **kw):
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
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # JSON (principal)
    @http.route('/spw/add_to_cart', type='json', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        data = request.jsonrequest or {}
        return self._do_add_to_cart(data)

    # HTTP (fallback robusto para cuando el JSON da guerra)
    @http.route('/spw/add_to_cart_http', type='http', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_add_to_cart_http(self, **post):
        try:
            raw = request.httprequest.get_data(cache=False, as_text=True) or ''
            data = json.loads(raw) if raw else post
        except Exception:
            data = post
        res = self._do_add_to_cart(data)
        body = json.dumps(res)
        return request.make_response(body, headers=[('Content-Type', 'application/json')])

    # Lógica compartida
    def _do_add_to_cart(self, data):
        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        tech = data.get('tech') or ''
        svg_color = data.get('svg_color') or ''
        notes = data.get('notes') or ''
        png_b64 = data.get('png_b64') or ''

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        order = request.website.sale_get_order(force_create=True)
        order._cart_update(product_id=variant.id, add_qty=qty)

        line = order.order_line.filtered(lambda l: l.product_id.id == variant.id)
        line = line.sorted('id')[-1] if line else False

        if line:
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
                    'datas': png_b64,
                    'type': 'binary',
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        return {'ok': True, 'cart_url': '/shop/cart'}