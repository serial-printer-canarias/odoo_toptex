# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Un identificador por personalización (no se copia ni se rellena solo)
    spw_token = fields.Char(index=True, copy=False)