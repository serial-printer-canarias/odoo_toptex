# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class SPWController(http.Controller):

    @http.route(['/personalizar/<int:tmpl_id>'], type='http', auth='public', website=True, sitemap=False)
    def customizer(self, tmpl_id, variant_id=None, **kw):
        tmpl = request.env['product.template'].sudo().browse(tmpl_id)
        if not tmpl.exists():
            return request.not_found()

        variant = None
        if variant_id:
            variant = request.env['product.product'].sudo().browse(int(variant_id))
            if not variant.exists() or variant.product_tmpl_id.id != tmpl.id:
                variant = None

        if variant and variant.image_1920:
            base_image_url = f'/web/image/product.product/{variant.id}/image_1920'
        else:
            base_image_url = f'/web/image/product.template/{tmpl.id}/image_1920'

        # Paleta NS300 (ejemplo; amplía libremente)
        ns_colors = [
            {"code": "000", "name": "Black",   "hex": "#000000"},
            {"code": "001", "name": "White",   "hex": "#FFFFFF"},
            {"code": "002", "name": "Navy",    "hex": "#001F3F"},
            {"code": "003", "name": "Royal",   "hex": "#2145FF"},
            {"code": "004", "name": "Red",     "hex": "#D81B24"},
            {"code": "005", "name": "Green",   "hex": "#1E7F33"},
            {"code": "006", "name": "Grey",    "hex": "#8A8A8A"},
            {"code": "007", "name": "Yellow",  "hex": "#FFCC00"},
        ]
        techniques = ["Sin vinilo", "Vinilo textil", "DTF", "Bordado", "Marcado en cuero"]

        return request.render('serial_printer_custom_wizard.customizer_page', {
            'tmpl': tmpl,
            'variant': variant,
            'base_image_url': base_image_url,
            'ns_colors_json': json.dumps(ns_colors),
            'techniques': techniques,
        })

    @http.route('/personalizar/add', type='http', auth='public', website=True, csrf=False)
    def customizer_add(self, **post):
        qty         = int(post.get('qty', 1))
        variant_id  = int(post.get('variant_id'))
        notes       = post.get('notes') or ''
        technique   = post.get('technique') or ''
        color_code  = post.get('color_code') or ''
        color_hex   = post.get('color_hex') or ''
        areas       = post.get('areas') or ''          # CSV: pecho_izq,espalda,...
        params_json = post.get('params_json') or '{}'  # tamaño/rot/x/y
        preview_png = post.get('preview_png')          # dataURL 'data:image/png;base64,...'

        att_id = False
        if preview_png and preview_png.startswith('data:image'):
            b64 = preview_png.split(',', 1)[1]
            att = request.env['ir.attachment'].sudo().create({
                'name': f'custom_{variant_id}.png',
                'datas': b64,
                'mimetype': 'image/png',
                'public': True,
            })
            att_id = att.id

        order = request.website.sale_get_order(force_create=1)
        res = order._cart_update(product_id=variant_id, add_qty=qty)
        line = request.env['sale.order.line'].sudo().browse(res.get('line_id'))
        if line:
            line.write({
                'x_spw_technique': technique,
                'x_spw_color_code': color_code,
                'x_spw_color_hex': color_hex,
                'x_spw_positions': areas,
                'x_spw_notes': notes,
                'x_spw_logo_attachment_id': att_id or False,
                'x_spw_params_json': params_json,
            })
        return request.redirect('/shop/cart')