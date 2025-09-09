# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request


class SpwPersonalizar(http.Controller):

    @http.route(
        ['/personalizar/<int:product_id>',
         '/shop/personalizar/<int:product_id>'],
        type='http', auth='public', website=True, sitemap=False
    )
    def personalizar(self, product_id, **kwargs):
        """Página de personalización para un product.template."""
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.not_found()

        values = {
            'product': product,
            'main_object': product,                 # contexto editor
            'main_object_name': 'product.template', # contexto editor
        }
        return request.render('serial_printer_custom_wizard.personalizar', values)

    @http.route('/personalizar/submit', type='http', auth='public', website=True, csrf=True, sitemap=False)
    def personalizar_submit(self, **post):
        """Procesa el formulario de personalización:
           - crea adjunto del logo (si hay)
           - añade el producto al carrito con la cantidad indicada
           - guarda un mensaje con el detalle de personalización en el pedido
           - redirige al carrito
        """
        # Datos básicos
        product_tmpl_id = int(post.get('product_id', 0) or 0)
        qty = int(post.get('cantidad', 1) or 1)
        tecnica = (post.get('tecnica_personalizacion') or '').strip()
        posicion = (post.get('posicion_diseno') or '').strip()
        color = (post.get('color_impresion') or '').strip()
        obs = (post.get('observaciones') or '').strip()

        product_tmpl = request.env['product.template'].sudo().browse(product_tmpl_id)
        if not product_tmpl.exists():
            return request.redirect('/shop')

        # Carrito
        order = request.website.sale_get_order(force_create=True)

        # Adjuntar el logo al pedido (si viene archivo)
        attachment_id = False
        upfile = request.httprequest.files.get('logo')
        if upfile:
            data = base64.b64encode(upfile.read())
            attachment = request.env['ir.attachment'].sudo().create({
                'name': upfile.filename or 'logo_personalizacion',
                'datas': data,
                'mimetype': upfile.mimetype or 'application/octet-stream',
                'res_model': 'sale.order',
                'res_id': order.id,
                'public': True,
            })
            attachment_id = attachment.id

        # Añadir producto (variante por defecto) al carrito
        product_variant = product_tmpl.product_variant_id
        order.sudo()._cart_update(product_id=product_variant.id, add_qty=qty)

        # Mensaje con el detalle
        detalle = (
            f"<p><b>Personalización</b> para <b>{product_tmpl.display_name}</b></p>"
            f"<ul>"
            f"<li>Técnica: {tecnica or '-'} </li>"
            f"<li>Posición: {posicion or '-'} </li>"
            f"<li>Color: {color or '-'} </li>"
            f"<li>Cantidad: {qty}</li>"
            f"</ul>"
        )
        if obs:
            detalle += f"<p><b>Observaciones:</b> {obs}</p>"

        kwargs = {'body': detalle}
        if attachment_id:
            kwargs['attachment_ids'] = [(4, attachment_id)]
        order.sudo().message_post(**kwargs)

        # Ir al carrito
        return request.redirect('/shop/cart')