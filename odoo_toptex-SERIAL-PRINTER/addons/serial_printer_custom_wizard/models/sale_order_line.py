# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_personalization_json = fields.Text('Personalización (JSON)')
    # Importante: attachment=True para guardarlo como ir.attachment
    x_personalization_png = fields.Binary('Mockup PNG', attachment=True)
    x_personalization_filename = fields.Char('Nombre PNG')