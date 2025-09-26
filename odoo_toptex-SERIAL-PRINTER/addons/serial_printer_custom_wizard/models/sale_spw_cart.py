# -*- coding: utf-8 -*-
from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        """
        Si recibimos spw_token, sólo permitimos casar con una línea que tenga
        el MISMO token. Si no coincide, devolvemos vacío para que cree una nueva.
        """
        res = super()._cart_find_product_line(product_id=product_id, line_id=line_id, **kwargs)
        token = kwargs.get('spw_token')
        if token:
            res = res.filtered(lambda l: l.spw_token == token)
        return res

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """
        Tras crear/actualizar la línea, si hay spw_token lo fijamos en la línea.
        """
        token = kwargs.get('spw_token')
        out = super()._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if token and out.get('line_id'):
            self.env['sale.order.line'].sudo().browse(out['line_id']).write({'spw_token': token})
        return out