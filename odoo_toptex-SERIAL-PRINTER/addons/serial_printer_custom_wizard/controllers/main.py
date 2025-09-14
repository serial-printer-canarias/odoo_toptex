# addons/serial_printer_custom_wizard/controllers/main.py
from odoo import http
from odoo.http import request
import base64
import json

class SPWController(http.Controller):

    @http.route(['/spw/customize/<int:variant_id>',
                 '/spw/customize'], type='http', auth='public', website=True, sitemap=False)
    def spw_customize(self, variant_id=None, **kw):
        """Renderiza la página del personalizador con la imagen correcta de variante o plantilla."""
        product_tmpl = None
        product = None
        if variant_id:
            product = request.env['product.product'].sudo().browse(int(variant_id))
            if product.exists():
                product_tmpl = product.product_tmpl_id
        if not product_tmpl and kw.get('template_id'):
            product_tmpl = request.env['product.template'].sudo().browse(int(kw['template_id']))

        if not product_tmpl:
            return request.not_found()

        # Imagen principal según variante/plantilla
        img_src = None
        if product and product.image_1920:
            img_src = f"/web/image/product.product/{product.id}/image_1920"
        elif product_tmpl.image_1920:
            img_src = f"/web/image/product.template/{product_tmpl.id}/image_1920"
        else:
            img_src = "/web/static/img/placeholder.png"

        values = {
            'template': product_tmpl,
            'variant_id': product.id if product else '',
            'img_src': img_src,
        }
        return request.render('serial_printer_custom_wizard.spw_customize_page', values)

    @http.route('/spw/add_to_cart', type='json', auth='public', website=True, csrf=False)
    def spw_add_to_cart(self, **kwargs):
        """
        Crea (o usa) el pedido web, añade la línea del producto
        y guarda la personalización como adjuntos (PNG + JSON).
        """
        try:
            template_id = int(kwargs.get('template_id') or 0)
            variant_id = kwargs.get('variant_id')
            variant_id = int(variant_id) if variant_id else 0
            qty = int(kwargs.get('qty') or 1)
            customization = kwargs.get('customization') or {}

            ProductProduct = request.env['product.product'].sudo()
            ProductTemplate = request.env['product.template'].sudo()

            product = None
            if variant_id:
                product = ProductProduct.browse(variant_id)
            elif template_id:
                tmpl = ProductTemplate.browse(template_id)
                product = tmpl.product_variant_id

            if not product or not product.exists():
                return {'ok': False, 'error': 'Producto no encontrado'}

            order = request.website.sale_get_order(force_create=True)
            res = order._cart_update(product_id=product.id, add_qty=qty)
            line_id = res.get('line_id')
            line = request.env['sale.order.line'].sudo().browse(line_id) if line_id else None

            # Añadir texto útil a la línea
            if line and customization:
                parts = []
                if customization.get('technique'):
                    parts.append(f"Técnica: {customization.get('technique')}")
                if customization.get('color'):
                    parts.append(f"Color: {customization.get('color')}")
                if customization.get('notes'):
                    parts.append(f"Obs.: {customization.get('notes')}")
                if parts:
                    line.name = (line.name or '') + " | " + " / ".join(parts)

            # Guardar adjuntos en el pedido (y referenciar línea en el nombre)
            if customization:
                Attach = request.env['ir.attachment'].sudo()

                # PNG de la previsualización
                preview_png = customization.get('preview_png')
                if preview_png and preview_png.startswith('data:image/png;base64,'):
                    png_b64 = preview_png.split(',', 1)[1]
                    Attach.create({
                        'name': f'Personalizacion_{product.display_name}.png',
                        'type': 'binary',
                        'datas': png_b64,
                        'res_model': 'sale.order',
                        'res_id': order.id,
                        'mimetype': 'image/png',
                        'description': f'Vista previa vinculada a la línea {line.id if line else "-"}',
                    })

                # JSON con parámetros
                Attach.create({
                    'name': f'Personalizacion_{product.display_name}.json',
                    'type': 'binary',
                    'datas': base64.b64encode(json.dumps(customization, ensure_ascii=False).encode('utf-8')),
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': 'application/json',
                    'description': f'Parámetros vinculados a la línea {line.id if line else "-"}',
                })

            return {'ok': True, 'order_id': order.id, 'line_id': line_id}
        except Exception as e:
            # Log y respuesta segura
            request.env.cr.rollback()
            return {'ok': False, 'error': str(e)}