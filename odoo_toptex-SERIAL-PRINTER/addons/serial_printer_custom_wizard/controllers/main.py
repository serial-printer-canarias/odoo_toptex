# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json  # <- lo usamos para parsear/serializar

class SpwCustomizer(http.Controller):

    # Página del personalizador (sin cambios funcionales)
    @http.route(
        ['/spw/customize/<int:template_id>', '/spw/customize'],
        type='http', auth='public', website=True, sitemap=False
    )
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        # Compatibilidad con querystring
        if template_id is None:
            q_tid = kw.get('template_id') or request.params.get('template_id')
            template_id = int(q_tid) if q_tid else None
        q_vid = variant_id or kw.get('variant_id') or request.params.get('variant_id')
        variant_id = int(q_vid) if q_vid else None

        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        template = ProductTmpl.browse(template_id) if template_id else ProductTmpl.browse()
        variant = Product.browse(variant_id) if variant_id else Product.browse()

        # URL de imagen base
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

    # === Añadir al carrito con personalización (versión HTTP robusta) ===
    @http.route('/spw/add_to_cart', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        # 1) Parseo seguro del JSON
        data = {}
        try:
            # Disponible en werkzeug; fuerza JSON cuando viene con Content-Type: application/json
            data = request.httprequest.get_json(force=True, silent=True) or {}
        except Exception:
            try:
                raw = request.httprequest.data
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode('utf-8', errors='ignore')
                    data = json.loads(raw) if raw else {}
            except Exception:
                data = {}

        # 2) Validación de parámetros
        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            resp = {'ok': False, 'message': 'Parámetros inválidos.'}
            return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])

        if not variant_id or qty <= 0:
            resp = {'ok': False, 'message': 'Parámetros inválidos.'}
            return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])

        tech = data.get('tech') or ''
        svg_color = data.get('svg_color') or ''
        notes = data.get('notes') or ''
        png_b64 = data.get('png_b64') or ''

        # 3) Buscar variante
        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            resp = {'ok': False, 'message': 'Variante no encontrada.'}
            return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])

        # 4) Pedido web y actualización de carrito
        order = request.website.sale_get_order(force_create=True)
        # Usamos el retorno para obtener la línea exacta creada/actualizada
        res = order.sudo()._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

        # 5) Guardar extras y adjunto
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
                line.write({'name': base_name + "\n" + " | ".join(extras)})

            if png_b64:
                request.env['ir.attachment'].sudo().create({
                    'name': 'personalizacion.png',
                    'type': 'binary',
                    'datas': png_b64,   # base64 sin prefijo
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        # 6) Respuesta JSON
        resp = {'ok': True, 'cart_url': '/shop/cart'}
        return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])