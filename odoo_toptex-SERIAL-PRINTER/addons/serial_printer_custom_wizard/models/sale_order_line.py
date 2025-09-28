# -*- coding: utf-8 -*-
# addons/serial_printer_custom_wizard/models/sale_order_line.py

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # --- Campos de personalización (DB) ---
    spw_svg_color = fields.Char(
        string="SPW SVG Color",
        help="Color elegido para el logo (ej. #2060FF).",
        copy=True,
    )
    spw_notes = fields.Text(
        string="SPW Notes",
        help="Observaciones de la personalización para el taller.",
        copy=True,
    )
    spw_png_attachment_id = fields.Many2one(
        "ir.attachment",
        string="SPW PNG",
        help="PNG renderizado de la personalización.",
        copy=False,
        ondelete="set null",
    )

    # URL de conveniencia para el preview; tus JS pueden usarla si lo necesitan
    spw_png_url = fields.Char(
        string="SPW PNG URL", compute="_compute_spw_png_url", store=False
    )

    @api.depends("id")
    def _compute_spw_png_url(self):
        for line in self:
            line.spw_png_url = f"/spw/line_preview/{line.id}.png" if line.id else False

    # ----------------- helpers internos -----------------

    def _spw_link_latest_png(self):
        """Si la línea no tiene PNG vinculado, intenta enlazar el último PNG
        adjuntado a esta sale.order.line (sin tocar controllers)."""
        Attach = self.env["ir.attachment"].sudo()
        for line in self:
            if not line.id:
                continue
            # Si ya hay PNG y es válido, no hacemos nada
            if line.spw_png_attachment_id and line.spw_png_attachment_id.exists():
                continue
            att = Attach.search(
                [
                    ("res_model", "=", "sale.order.line"),
                    ("res_id", "=", line.id),
                    ("mimetype", "in", ["image/png", "image/x-png"]),
                ],
                order="id desc",
                limit=1,
            )
            if att:
                # evitar recursión en write
                line.sudo().with_context(mail_notrack=True).write(
                    {"spw_png_attachment_id": att.id}
                )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Por si el adjunto ya existiera antes de llenar el campo
        rec._spw_link_latest_png()
        return rec

    def write(self, vals):
        res = super().write(vals)
        # Si tras este write existe un PNG adjunto, lo enlazamos
        self._spw_link_latest_png()
        return res


# ======================================================================
# Enlaza automáticamente el PNG con la línea cuando se crea/escribe
# un ir.attachment apuntando a sale.order.line (solo models, sin controllers)
# ======================================================================

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _spw_bind_to_sale_line(self):
        """Si el adjunto es un PNG y apunta a una sale.order.line, lo
        enlazamos en spw_png_attachment_id si es más reciente."""
        for att in self:
            if (
                att.res_model == "sale.order.line"
                and att.res_id
                and att.mimetype in ("image/png", "image/x-png")
            ):
                sol = self.env["sale.order.line"].sudo().browse(att.res_id)
                if not sol.exists():
                    continue
                if (
                    not sol.spw_png_attachment_id
                    or att.id > sol.spw_png_attachment_id.id
                ):
                    sol.sudo().with_context(mail_notrack=True).write(
                        {"spw_png_attachment_id": att.id}
                    )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._spw_bind_to_sale_line()
        return rec

    def write(self, vals):
        res = super().write(vals)
        self._spw_bind_to_sale_line()
        return res