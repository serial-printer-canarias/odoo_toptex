# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_tech = fields.Char(string='SPW Técnica')
    spw_svg_color = fields.Char(string='SPW Color SVG')
    spw_notes = fields.Text(string='SPW Notas')