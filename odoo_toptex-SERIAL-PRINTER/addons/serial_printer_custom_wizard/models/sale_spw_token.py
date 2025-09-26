# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_token = fields.Char(index=True, copy=False, help="Identificador único por personalización para no fusionar líneas.")