# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import json

class SpwCustomizer(http.Controller):

    # --- Página de personalización (ya la tienes funcionando) ---
    @http.route(['/spw/customize'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, template_id=None, variant_id=None, **kw):
        ProductTmpl = request.env['product.template'].sudo()
        Product = request.env['product.product'].sudo()

        template = ProductTmpl.browse(int(template_id)) if template_id else None
        variant = Product.browse(int(variant_id)) if variant_id else None

        # Imagen base (la de la variante o, si no, la del template)
        img_src = ''
        if variant and variant.image_1920:
            img_src = f"/web/image/product.product/{variant.id}/image_1920"
        elif template and template.image_1920:
            img_src = f"/web/image/product.template/{template.id}/image_1920"

        values = {
            'template': template,
            'variant_id': variant.id if variant else False,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # --- NUEVO: añadir al carrito con personalización ---
    @http.route('/spw/add_to_cart', type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **kw):
        """
        Espera un JSON con:
        {
            "variant_id": int,
            "qty": int,
            "tech": "Serigrafía|DTF|Bordado",
            "svg_color": "#RRGGBB" (opcional),
            "notes": "texto",
            "png_b64": "..." (sin prefijo data:)
        }
        """
        data = request.jsonrequest or {}
        variant_id = int(data.get('variant_id') or 0)
        qty = int(data.get('qty') or 1)
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

        # Obtener/crear pedido web
        order = request.website.sale_get_order(force_create=True)
        # Añadir línea al carrito
        order._cart_update(product_id=variant.id, add_qty=qty)

        # Recuperar la línea recién añadida (última de ese producto)
        line = order.order_line.filtered(lambda l: l.product_id.id == variant.id)
        line = line.sorted('id')[-1] if line else False

        if line:
            # Adjuntamos la info de personalización en el nombre de la línea
            extra = []
            if tech:
                extra.append(f"Técnica: {tech}")
            if svg_color:
                extra.append(f"Color SVG: {svg_color}")
            if notes:
                extra.append(f"Obs: {notes}")
            if extra:
                new_name = (line.name or variant.get_product_multiline_description_sale() or variant.display_name) + "\n" + " | ".join(extra)
                line.sudo().write({'name': new_name})

            # Guardar el PNG como adjunto en la línea
            if png_b64:
                request.env['ir.attachment'].sudo().create({
                    'name': 'personalizacion.png',
                    'datas': png_b64,
                    'res_model': 'sale.order.line',
                    'res_id': line.id,
                    'mimetype': 'image/png',
                })

        return {'ok': True, 'cart_url': '/shop/cart'}