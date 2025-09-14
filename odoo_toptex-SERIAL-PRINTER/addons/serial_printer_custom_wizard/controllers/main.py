# addons/serial_printer_custom_wizard/controllers/main.py
from odoo import http
from odoo.http import request

class SPWCustomizer(http.Controller):

    @http.route(['/spw/customize/<int:template_id>'], type='http', auth='public', website=True)
    def spw_customize(self, template_id, **kw):
        """Página del personalizador."""
        variant_id = int(kw.get('variant_id') or 0) or False
        template = request.env['product.template'].sudo().browse(template_id)

        if variant_id:
            img_src = f"/web/image/product.product/{variant_id}/image_1920"
        else:
            img_src = f"/web/image/product.template/{template.id}/image_1920"

        qcontext = {
            'template': template,
            'variant_id': variant_id,
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', qcontext)

    @http.route('/spw/add_to_cart', type='json', auth='public', website=True, csrf=False)
    def spw_add_to_cart(self, **post):
        """Crea la línea del carrito con notas y adjunta el PNG de la personalización."""
        data = request.jsonrequest or post
        template_id = int(data.get('template_id') or 0)
        variant_id = int(data.get('variant_id') or 0) or False
        qty        = float(data.get('qty') or 1)
        notes      = (data.get('notes') or '').strip()
        tech       = (data.get('tech') or '').strip()
        svg_color  = (data.get('svg_color') or '').strip()
        preview    = data.get('preview_png')  # dataURL

        ProductProduct = request.env['product.product'].sudo()
        if variant_id:
            product = ProductProduct.browse(variant_id)
        else:
            tmpl = request.env['product.template'].sudo().browse(template_id)
            product = tmpl.product_variant_id

        order = request.website.sale_get_order(force_create=True)

        # Línea con detalle de la personalización en el nombre
        name = f"{product.display_name}\n[Personalización] Técnica: {tech or '-'}  Color: {svg_color or '-'}"
        if notes:
            name += f"\nNotas: {notes}"

        line_vals = {
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'name': name,
        }
        request.env['sale.order.line'].sudo().create(line_vals)

        # Adjuntar PNG al pedido
        if preview and isinstance(preview, str) and preview.startswith('data:image'):
            try:
                header, b64 = preview.split(',', 1)
                request.env['ir.attachment'].sudo().create({
                    'name': f'personalizacion_{product.id}.png',
                    'type': 'binary',
                    'datas': b64,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': 'image/png',
                })
            except Exception:
                pass

        return {'ok': True, 'cart_url': '/shop/cart'}