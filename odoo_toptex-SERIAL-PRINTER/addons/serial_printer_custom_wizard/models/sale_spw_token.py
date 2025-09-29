# -*- coding: utf-8 -*-
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    spw_token = fields.Char(index=True)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        line = super()._cart_find_product_line(product_id=product_id, line_id=line_id, **kwargs)
        token = kwargs.get('spw_token')
        if token and line and getattr(line, 'spw_token', False) != token:
            # No coinciden → devolvemos "no match" para forzar NUEVA línea
            return self.env['sale.order.line']
        return line