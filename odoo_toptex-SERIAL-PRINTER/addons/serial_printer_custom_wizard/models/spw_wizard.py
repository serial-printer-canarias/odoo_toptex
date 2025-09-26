# -*- coding: utf-8 -*-
import base64
from odoo import models

class SPWWizard(models.TransientModel):
    _name = 'spw.wizard'            # <-- usa el nombre real de tu wizard
    _description = 'Serial Printer Wizard'

    # ... tus fields / métodos previos ...

    def _spw_append_preview(self, line, b64_bytes, mimetype='image/png'):
        """
        Añade la siguiente preview (1..N) a la línea sin pisar las anteriores.
        b64_bytes debe ser imagen en base64 (no bytes crudos).
        """
        Attach = self.env['ir.attachment'].sudo()

        # calcular siguiente índice existente: spw_preview_<line_id>_<i>.png
        existing = Attach.search_read([
            ('res_model', '=', 'sale.order.line'),
            ('res_id', '=', line.id),
            ('type', '=', 'binary'),
            ('name', 'like', 'spw_preview_%s_' % line.id),
        ], ['name'], limit=0)

        next_idx = 1
        if existing:
            try:
                next_idx = max(int(a['name'].rsplit('_', 1)[1].split('.')[0]) for a in existing) + 1
            except Exception:
                next_idx = len(existing) + 1

        name = 'spw_preview_%s_%s.png' % (line.id, next_idx)
        Attach.create({
            'name': name,
            'res_model': 'sale.order.line',
            'res_id': line.id,
            'type': 'binary',
            'mimetype': mimetype,
            'datas': b64_bytes,  # ya en base64
        })