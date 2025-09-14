# addons/serial_printer_custom_wizard/controllers/main.py
# -*- coding: utf-8 -*-

import base64
from odoo import http
from odoo.http import request

class SpwController(http.Controller):

    # Página de personalización
    @http.route('/spw/customize/<int:template_id>', auth='public', website=True)
    def spw_customize(self, template_id, **kw):
        """Muestra la página de personalización con la imagen correcta.
        Prioriza imagen de la variante (variant_id) y, si no hay, usa la del template.
        """
        template = request.env['product.template'].sudo().browse(template_id)
        if not template.exists():
            return request.not_found()

        variant_id = kw.get('variant_id')
        img_src = None

        # Imagen de la variante si viene y existe
        if variant_id:
            try:
                variant_id_int = int(variant_id)
            except Exception:
                variant_id_int = False
            if variant_id_int:
                variant = request.env['product.product'].sudo().browse(variant_id_int)
                if variant.exists():
                    # Si la variante tiene imagen, úsala; si no, cae al template
                    if variant.image_1920:
                        img_src = f"/web/image/product.product/{variant.id}/image_1920"

        # Imagen del template si no hay variante válida
        if not img_src:
            img_src = f"/web/image/product.template/{template.id}/image_1920"

        values = {
            'template': template,
            'variant_id': variant_id or '',
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    # Añadir al carrito con la personalización
    @http.route('/spw/add_to_cart', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def spw_add_to_cart(self, **post):
        """Recibe un JSON (fetch) con:
           - template_id, variant_id, quantity
           - png_data (dataURL del montaje)
           - technique, notes, svg_color
        Crea línea en carrito, adjunta PNG a la línea y añade detalles a la descripción.
        """
        payload = request.jsonrequest or {}
        template_id = int(payload.get('template_id') or 0)
        variant_id = int(payload.get('variant_id') or 0)
        quantity = float(payload.get('quantity') or 1)
        technique = (payload.get('technique') or '').strip()
        notes = (payload.get('notes') or '').strip()
        svg_color = (payload.get('svg_color') or '').strip()
        png_data = payload.get('png_data') or ''

        env = request.env.sudo()

        # Producto/variante a añadir
        product = None
        if variant_id:
            product = env['product.product'].browse(variant_id)
            if not product.exists():
                product = None
        if not product and template_id:
            tmpl = env['product.template'].browse(template_id)
            if tmpl.exists():
                product = tmpl.product_variant_id

        if not product:
            return request.make_json_response({'ok': False, 'error': 'Producto no encontrado'})

        # Obtener/crear pedido del sitio
        order = request.website.sale_get_order(force_create=1)

        # Añadir línea
        res = order._cart_update(product_id=product.id, add_qty=quantity)
        line = env['sale.order.line'].browse(res.get('line_id'))

        # Guardar adjunto PNG si llega
        if png_data.startswith('data:image/png;base64,'):
            b64 = png_data.split(',', 1)[1]
            try:
                raw = base64.b64decode(b64)
            except Exception:
                raw = b64.encode()
            env['ir.attachment'].create({
                'name': f'personalizacion_{product.display_name}.png',
                'type': 'binary',
                'datas': base64.b64encode(raw),
                'res_model': 'sale.order.line',
                'res_id': line.id,
                'mimetype': 'image/png',
            })

        # Enriquecer el nombre de la línea con los detalles
        extra = []
        if technique:
            extra.append(f"Técnica: {technique}")
        if svg_color:
            extra.append(f"Color (SVG): {svg_color}")
        if notes:
            extra.append(f"Observaciones: {notes}")
        if extra:
            line.name = (line.name or product.display_name) + "\n" + "\n".join(extra)

        return request.make_json_response({
            'ok': True,
            'order_id': order.id,
            'line_id': line.id,
            'cart_url': '/shop/cart',
        })