# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_tech = fields.Char(string="SPW Técnica")
    spw_svg_color = fields.Char(string="SPW Color SVG")
    spw_notes = fields.Text(string="SPW Observaciones")
    spw_png_attachment_id = fields.Many2one('ir.attachment', string="SPW PNG adjunto", ondelete='set null')

    # Opcional: evitar duplicar líneas de técnica/color al cambiar nombre
    @api.onchange('spw_tech', 'spw_svg_color')
    def _onchange_spw_meta_to_description(self):
        for line in self:
            base = (line.name or '').splitlines()
            base_clean = [x for x in base if x and not x.startswith('Técnica:') and not x.startswith('Color SVG:')]
            if line.spw_tech:
                base_clean.append(f"Técnica: {line.spw_tech}")
            if line.spw_svg_color:
                base_clean.append(f"Color SVG: {line.spw_svg_color}")
            line.name = "\n".join(base_clean)