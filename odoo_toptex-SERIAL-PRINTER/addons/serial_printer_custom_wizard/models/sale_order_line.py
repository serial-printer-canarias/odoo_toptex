# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # IMPORTANTE: store=False para que NO requieran columna en BD
    spw_png_attachment_id = fields.Many2one(
        'ir.attachment',
        string='SPW PNG',
        compute='_compute_spw_fields',
        store=False,
        readonly=True,
    )
    spw_svg_color = fields.Char(
        string='SPW SVG Color',
        compute='_compute_spw_fields',
        store=False,
        readonly=True,
    )
    spw_notes = fields.Text(
        string='SPW Notes',
        compute='_compute_spw_fields',
        store=False,
        readonly=True,
    )

    @api.depends('name')
    def _compute_spw_fields(self):
        """ Valores seguros por defecto para que la web no rompa.
            - Busca el último adjunto de imagen ligado a la línea (si existe).
            - Intenta extraer un #RRGGBB del texto visible de la línea.
            - Deja notas a False (si luego las generas, perfecto).
        """
        Att = self.env['ir.attachment'].sudo()
        for line in self:
            # 1) Miniatura: último attachment image/* de la línea
            att = Att.search([
                ('res_model', '=', 'sale.order.line'),
                ('res_id', '=', line.id),
                ('mimetype', 'ilike', 'image/%'),
            ], order='id desc', limit=1)
            line.spw_png_attachment_id = att or False

            # 2) Color: buscar '#RRGGBB' en line.name sin usar regex
            txt = (line.name or '')
            pos = txt.rfind('#')
            hexval = False
            if pos != -1 and len(txt) >= pos + 7:
                cand = txt[pos:pos+7].upper()  # ej: #2060FF
                ok = True
                for c in cand[1:]:
                    if c not in '0123456789ABCDEF':
                        ok = False
                        break
                if ok:
                    hexval = cand
            line.spw_svg_color = hexval

            # 3) Notas: por defecto vacío/False
            line.spw_notes = False