# -*- coding: utf-8 -*-
from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    spw_custom_json = fields.Json(string="Personalización")
    spw_attachment_id = fields.Many2one("ir.attachment", string="Logo adjunto")