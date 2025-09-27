# -*- coding: utf-8 -*-
import re
from odoo import models, fields

META_RE = re.compile(r'^\s*(Técnica:|Tecnica:|SVG:|Color SVG:).*$',
                     flags=re.IGNORECASE | re.MULTILINE)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    spw_tech = fields.Char('SPW Technique')
    spw_svg_color = fields.Char('SPW SVG Color')
    spw_notes = fields.Text('SPW Notes')
    spw_preview_attachment_id = fields.Many2one('ir.attachment', string='SPW Preview')

    def _apply_spw_meta_to_name(self):
        for line in self:
            name = line.name or ''
            name = META_RE.sub('', name).rstrip()
            parts = []
            if line.spw_tech:
                parts.append('Técnica: %s' % line.spw_tech)
            if line.spw_svg_color:
                parts.append('Color SVG: %s' % line.spw_svg_color.upper())
            if parts:
                if name:
                    name += '\n'
                name += ' | '.join(parts)
            line.name = name

    def write(self, vals):
        res = super().write(vals)
        if {'spw_tech','spw_svg_color'} & set(vals.keys()):
            self._apply_spw_meta_to_name()
        return res

    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_spw_meta_to_name()
        return records