# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_spw_technique = fields.Char('Técnica')
    x_spw_color_code = fields.Char('Código color')
    x_spw_color_hex = fields.Char('Color HEX')
    x_spw_positions = fields.Char('Posiciones')  # pecho_izq,pecho_dcha,espalda,libre
    x_spw_notes = fields.Text('Observaciones')
    x_spw_logo_attachment_id = fields.Many2one('ir.attachment', string='Logo adjunto')
    x_spw_params_json = fields.Text('Parámetros de previsualización')