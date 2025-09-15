# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class SpwCustomizer(http.Controller):

    # === Página de personalización ===
    # Dejamos dos rutas para soportar: /spw/customize/<id> y /spw/customize?template_id=...&variant_id=...
    @http.route(
        ['/spw/customize/<int:template_id>', '/spw/customize'],
        type='http', auth='public', website=True, sitemap=False
    )
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        # Soportar parámetros por querystring también
        if template_id is None:
            tid = kw.get('template_id') or request.params.get('template_id')
            template_id = int(tid) if tid else None
        vid = variant_id or kw.get('variant_id') or request.params.get('variant_id')
        variant_id = int(vid) if vid else None

        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        template = ProductTmpl.browse(template_id) if template_id else ProductTmpl.browse()
        variant = Product.browse(variant_id) if variant_id else Product.browse()

        # URL de imagen de la variante (o la del template si no hay)
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

    # === Añadir al carrito con personalización (robusto) ===
    # IMPORTANTE: type='http' (no json) para no depender de jsonrpc; aceptamos JSON en el body.
    @http.route(
        '/spw/add_to_cart', type='http', auth='public', website=True, csrf=False, methods=['POST']
    )
    def spw_add_to_cart(self, **kw):
        """
        Espera en el body JSON con:
          {
            "variant_id": int,
            "qty": int,
            "tech": "Serigrafía|DTF|Bordado",
            "svg_color": "#RRGGBB" (opcional),
            "notes": "texto",
            "png_b64": "..."  # base64 del PNG sin prefijo data:
          }
        La respuesta es JSON: {"ok": True, "cart_url": "/shop/cart"}
        """
        # 1) Leer body JSON venga como venga
        data = {}
        try:
            # a) JSON directo (fetch con Content-Type: application/json)
            data = request.httprequest.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        if not data:
            # b) Raw body → intentar json.loads
            raw = request.httprequest.data
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode('utf-8', errors='ignore')
                try:
                    data = json.loads(raw) if raw else {}
                except Exception:
                    data = {}

        # 2) Validación
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

        # 3) Producto y pedido web
        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            resp = {'ok': False, 'message': 'Variante no encontrada.'}
            return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])

        order = request.website.sale_get_order(force_create=True)
        res = order.sudo()._cart_update(product_id=variant.id, add_qty=qty) or {}
        line_id = res.get('line_id')
        line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

        # 4) Extras + adjunto PNG
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
                    'datas': png_b64,              # base64 ya limpio (sin 'data:')
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        resp = {'ok': True, 'cart_url': '/shop/cart'}
        return request.make_response(json.dumps(resp), headers=[('Content-Type', 'application/json')])