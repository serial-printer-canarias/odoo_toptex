# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_meta    = fields.Text(string='SPW Meta')
    spw_color   = fields.Char(string='SPW Color')
    spw_preview = fields.Binary(string='SPW Preview', attachment=True)