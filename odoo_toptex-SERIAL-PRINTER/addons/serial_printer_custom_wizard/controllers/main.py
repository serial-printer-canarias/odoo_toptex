# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class SpwCustomizer(http.Controller):

    # Página del personalizador (soporta /spw/customize/<id> y ?variant_id=)
    @http.route(['/spw/customize/<int:template_id>', '/spw/customize'], type='http',
                auth='public', website=True, sitemap=False)
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

    # Añadir al carrito con la personalización
    @http.route('/spw/add_to_cart', type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        """
        JSON esperado:
        {
            "variant_id": int,
            "qty": int,
            "tech": "Serigrafía|DTF|Bordado",
            "svg_color": "#RRGGBB" (opcional),
            "notes": "texto",
            "png_b64": "..."  # base64 SIN prefijo data:
        }
        """
        data = request.jsonrequest or {}
        try:
            variant_id = int(data.get('variant_id') or 0)
            qty = int(data.get('qty') or 1)
        except Exception:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        if not variant_id or qty <= 0:
            return {'ok': False, 'message': 'Parámetros inválidos.'}

        Product = request.env['product.product'].sudo()
        variant = Product.browse(variant_id)
        if not variant.exists():
            return {'ok': False, 'message': 'Variante no encontrada.'}

        tech = data.get('tech') or ''
        svg_color = data.get('svg_color') or ''
        notes = data.get('notes') or ''
        png_b64 = data.get('png_b64') or ''

        # Pedido web
        order = request.website.sale_get_order(force_create=True)

        # Usamos el retorno de _cart_update para obtener la línea con fiabilidad
        res = order.sudo()._cart_update(product_id=variant.id, add_qty=qty)
        line_id = (res or {}).get('line_id')
        line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else False

        if line and line.exists():
            # Texto extra en la línea
            extra_bits = []
            if tech:
                extra_bits.append(f"Técnica: {tech}")
            if svg_color:
                extra_bits.append(f"Color SVG: {svg_color}")
            if notes:
                extra_bits.append(f"Obs: {notes}")

            if extra_bits:
                base_name = line.name or variant.get_product_multiline_description_sale() or variant.display_name
                line.write({'name': base_name + "\n" + " | ".join(extra_bits)})

            # Adjuntamos el PNG
            if png_b64:
                request.env['ir.attachment'].sudo().create({
                    'name': 'personalizacion.png',
                    'type': 'binary',
                    'datas': png_b64,     # ya viene en base64
                    'mimetype': 'image/png',
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                })

        return {'ok': True, 'cart_url': '/shop/cart'}