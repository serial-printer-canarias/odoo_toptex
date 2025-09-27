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
        svg_color = (data.get('svg_color') or '').strip()
        notes = (data.get('notes') or '').strip()

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        order = request.website.sale_get_order(force_create=True)
        res = order._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        if not line_id:
            # Fallback: última línea con ese producto
            line = order.order_line.filtered(lambda l: l.product_id.id == variant.id).sorted('id')[-1:] or False
            line = line and line[0] or False
            line_id = line.id if line else False

        if not line_id:
            return {'ok': False, 'message': 'No se pudo crear la línea del carrito.'}

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if line.exists():
            extras = []
            if tech:
                extras.append(f"Técnica: {tech}")
            if svg_color:
                extras.append(f"Color SVG: {svg_color}")
            if notes:
                extras.append(f"Obs: {notes}")
            if extras:
                base_name = line.name or line.product_id.get_product_multiline_description_sale() or line.product_id.display_name
                line.write({'name': base_name + "\n" + " | ".join(extras)})

        return {'ok': True, 'line_id': line_id, 'cart_url': '/shop/cart'}

    # Fallback HTTP (por si algún navegador bloquea JSON)
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart_meta_http(self, **kw):
        try:
            variant_id = int(kw.get('variant_id') or 0)
            qty = int(kw.get('qty') or 1)
        except Exception:
            return Response('{"ok": false, "message": "Parámetros inválidos."}', mimetype='application/json')

        tech = (kw.get('tech') or '').strip()
        svg_color = (kw.get('svg_color') or '').strip()
        notes = (kw.get('notes') or '').strip()

        if not variant_id or qty <= 0:
            return Response('{"ok": false, "message": "Parámetros inválidos."}', mimetype='application/json')

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return Response('{"ok": false, "message": "Variante no encontrada."}', mimetype='application/json')

        order = request.website.sale_get_order(force_create=True)
        res = order._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        if not line_id:
            line = order.order_line.filtered(lambda l: l.product_id.id == variant.id).sorted('id')[-1:] or False
            line = line and line[0] or False
            line_id = line.id if line else False

        if not line_id:
            return Response('{"ok": false, "message": "No se pudo crear la línea del carrito."}', mimetype='application/json')

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if line.exists():
            extras = []
            if tech:
                extras.append(f"Técnica: {tech}")
            if svg_color:
                extras.append(f"Color SVG: {svg_color}")
            if notes:
                extras.append(f"Obs: {notes}")
            if extras:
                base_name = line.name or line.product_id.get_product_multiline_description_sale() or line.product_id.display_name
                line.write({'name': base_name + "\n" + " | ".join(extras)})

        return Response(f'{{"ok": true, "line_id": {line_id}, "cart_url": "/shop/cart"}}', mimetype='application/json')

    # ====== CARRITO: SEGUNDA LLAMADA (adjunta PNG a la línea) ======
    @http.route('/spw/attach_png', type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_attach_png(self, **kw):
        data = request.jsonrequest or {}
        try:
            line_id = int(data.get('line_id') or 0)
        except Exception:
            line_id = 0
        png_b64 = data.get('png_b64') or ''
        if not (line_id and png_b64):
            return {'ok': False, 'message': 'Faltan datos.'}

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return {'ok': False, 'message': 'Línea no encontrada.'}

        request.env['ir.attachment'].sudo().create({
            'name': f'spw_line_{line_id}.png',
            'datas': png_b64,
            'type': 'binary',
            'mimetype': 'image/png',
            'res_model': 'sale.order.line',
            'res_id': line_id,
        })
        return {'ok': True}

    # Fallback HTTP
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_attach_png_http(self, **kw):
        try:
            line_id = int(kw.get('line_id') or 0)
        except Exception:
            line_id = 0
        png_b64 = kw.get('png_b64') or ''
        if not (line_id and png_b64):
            return Response('{"ok": false, "message": "Faltan datos."}', mimetype='application/json')

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return Response('{"ok": false, "message": "Línea no encontrada."}', mimetype='application/json')

        request.env['ir.attachment'].sudo().create({
            'name': f'spw_line_{line_id}.png',
            'datas': png_b64,
            'type': 'binary',
            'mimetype': 'image/png',
            'res_model': 'sale.order.line',
            'res_id': line_id,
        })
        return Response('{"ok": true}', mimetype='application/json')

    # ====== PREVISUALIZACIÓN PNG EN CARRITO ======
    @http.route('/spw/line_preview/<int:line_id>.png', type='http', auth='public', website=True, sitemap=False)
    def spw_line_preview(self, line_id, **kw):
        Att = request.env['ir.attachment'].sudo()
        att = Att.search([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line_id),
            ('mimetype', '=', 'image/png'),
        ], order='id desc', limit=1)
        if not att:
            # PNG 1x1 transparente
            empty_png_b64 = (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
                "ASsJTYQAAAAASUVORK5CYII="
            )
            data = base64.b64decode(empty_png_b64)
        else:
            data = base64.b64decode(att.datas or b'')
        headers = [
            ('Content-Type', 'image/png'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
        ]
        return Response(data, headers=headers)