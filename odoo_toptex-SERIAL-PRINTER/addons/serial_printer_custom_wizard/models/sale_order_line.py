# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_tech = fields.Char(string="Técnica")
    spw_svg_color = fields.Char(string="Color SVG")
    spw_notes = fields.Text(string="Notas personalización")