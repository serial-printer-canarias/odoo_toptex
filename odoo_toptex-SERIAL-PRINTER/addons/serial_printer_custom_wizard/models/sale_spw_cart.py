# -*- coding: utf-8 -*-
from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        """Si recibimos spw_token, NO buscamos línea: forzamos crear una nueva.
        Sin token: nunca casar con líneas que ya tengan token (separar 'sin pers' vs 'con pers')."""
        token = kwargs.get('spw_token')
        if token:
            return self.env['sale.order.line']  # <- fuerza 'no match' => crea línea nueva
        lines = super()._cart_find_product_line(product_id=product_id, line_id=line_id, **kwargs)
        return lines.filtered(lambda l: not l.spw_token)

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        token = kwargs.get('spw_token')
        if token:
            line_id = None  # <- importantísimo: jamás actualizar línea existente
        res = super()._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        if token and res.get('line_id'):
            self.env['sale.order.line'].sudo().browse(res['line_id']).write({'spw_token': token})
        return res