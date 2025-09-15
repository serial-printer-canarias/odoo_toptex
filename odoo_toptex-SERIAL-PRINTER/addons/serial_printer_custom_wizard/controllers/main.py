# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json


class SpwCustomizer(http.Controller):

    # ---------------- Página ----------------
    @http.route(['/spw/customize/<int:template_id>', '/spw/customize'], type='http',
                auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        # permitir ?template_id= y ?variant_id=
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

    # ---------------- Helpers internos ----------------
    def _create_line_and_meta(self, variant_id, qty, tech, svg_color, notes):
        Product = request.env['product.product'].sudo()
        variant = Product.browse(int(variant_id))
        if not variant.exists():
            return (False, "Variante no encontrada.", None)

        order = request.website.sale_get_order(force_create=True)
        order._cart_update(product_id=variant.id, add_qty=int(qty))

        line = order.order_line.filtered(lambda l: l.product_id.id == variant.id)
        line = line.sorted('id')[-1] if line else False
        if not line:
            return (False, "No se pudo crear la línea.", None)

        # Texto visible en línea
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

        # JSON para taller
        cfg = {
            'variant_id': variant.id,
            'qty': int(qty),
            'tech': tech or '',
            'svg_color': svg_color or '',
            'notes': notes or '',
        }
        request.env['ir.attachment'].sudo().create({
            'name': f'personalizacion_{line.id}.json',
            'datas': base64.b64encode(json.dumps(cfg, ensure_ascii=False).encode('utf-8')),
            'type': 'binary',
            'mimetype': 'application/json',
            'res_model': 'sale.order.line',
            'res_id': line.id,
        })
        return (True, "", line)

    # ---------------- Paso 1 (JSON) ----------------
    @http.route('/spw/add_to_cart_meta', type='json', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_add_to_cart_meta(self, **kw):
        data = request.jsonrequest or {}
        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        ok, msg, line = self._create_line_and_meta(
            variant_id, qty,
            data.get('tech') or '',
            data.get('svg_color') or '',
            data.get('notes') or ''
        )
        if not ok:
            return {'ok': False, 'message': msg}
        return {'ok': True, 'cart_url': '/shop/cart', 'line_id': line.id}

    # ---------------- Paso 1 (HTTP fallback) ----------------
    @http.route('/spw/add_to_cart_meta_http', type='http', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_add_to_cart_meta_http(self, **kw):
        # aceptar form-data o json plano
        raw = request.httprequest.get_data(cache=False, as_text=True) or ''
        try:
            data = json.loads(raw) if raw and raw.strip().startswith('{') else dict(request.params)
        except Exception:
            data = dict(request.params)

        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            body = json.dumps({'ok': False, 'message': 'Parámetros inválidos.'})
            return request.make_response(body, headers=[('Content-Type', 'application/json')])

        ok, msg, line = self._create_line_and_meta(
            variant_id, qty,
            data.get('tech') or '',
            data.get('svg_color') or '',
            data.get('notes') or ''
        )
        out = {'ok': ok, 'message': msg or '', 'cart_url': '/shop/cart'}
        if ok and line:
            out['line_id'] = line.id
        return request.make_response(json.dumps(out), headers=[('Content-Type', 'application/json')])

    # ---------------- Paso 2 (JSON) ----------------
    @http.route('/spw/attach_png', type='json', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_attach_png(self, **kw):
        data = request.jsonrequest or {}
        try:
            line_id = int(data.get('line_id') or 0)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos.'}
        png_b64 = data.get('png_b64') or ''
        if not line_id or not png_b64:
            return {'ok': False, 'message': 'Falta PNG o línea.'}

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return {'ok': False, 'message': 'Línea no encontrada.'}

        request.env['ir.attachment'].sudo().create({
            'name': f'personalizacion_{line.id}.png',
            'datas': png_b64,
            'type': 'binary',
            'mimetype': 'image/png',
            'res_model': 'sale.order.line',
            'res_id': line.id,
        })
        return {'ok': True}

    # ---------------- Paso 2 (HTTP fallback) ----------------
    @http.route('/spw/attach_png_http', type='http', auth='public', website=True,
                csrf=False, methods=['POST'])
    def spw_attach_png_http(self, **kw):
        raw = request.httprequest.get_data(cache=False, as_text=True) or ''
        try:
            data = json.loads(raw) if raw and raw.strip().startswith('{') else dict(request.params)
        except Exception:
            data = dict(request.params)

        try:
            line_id = int(data.get('line_id') or 0)
        except Exception:
            body = json.dumps({'ok': False, 'message': 'Parámetros inválidos.'})
            return request.make_response(body, headers=[('Content-Type', 'application/json')])
        png_b64 = data.get('png_b64') or ''
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists() or not png_b64:
            out = {'ok': False, 'message': 'Falta PNG o línea.'}
            return request.make_response(json.dumps(out), headers=[('Content-Type', 'application/json')])

        request.env['ir.attachment'].sudo().create({
            'name': f'personalizacion_{line.id}.png',
            'datas': png_b64,
            'type': 'binary',
            'mimetype': 'image/png',
            'res_model': 'sale.order.line',
            'res_id': line.id,
        })
        return request.make_response(json.dumps({'ok': True}), headers=[('Content-Type', 'application/json')])