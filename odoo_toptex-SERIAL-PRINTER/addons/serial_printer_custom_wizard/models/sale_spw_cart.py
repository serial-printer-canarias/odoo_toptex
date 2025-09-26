# -*- coding: utf-8 -*-
from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        lines = super()._cart_find_product_line(product_id=product_id, line_id=line_id, **kwargs)
        token = kwargs.get('spw_token')
        if token:
            # Sólo casar con la línea que tenga el mismo token
            return lines.filtered(lambda l: l.spw_token == token)
        # Sin token, nunca mezclar con líneas personalizadas
        return lines.filtered(lambda l: not l.spw_token)

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        token = kwargs.get('spw_token')
        # Si hay token, forzamos crear línea nueva
        if token:
            line_id = None
        res = super()._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if token and res.get('line_id'):
            self.env['sale.order.line'].sudo().browse(res['line_id']).write({'spw_token': token})
        return res