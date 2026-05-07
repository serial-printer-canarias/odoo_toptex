# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    personalization_order_ids = fields.One2many("sp.personalization.order", "account_move_id", string="Fichas personalización")
    personalization_count = fields.Integer(compute="_compute_personalization_count")

    def _compute_personalization_count(self):
        for move in self:
            move.personalization_count = len(move.personalization_order_ids)

    def action_create_personalization_order_from_invoice(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            raise UserError(_("Solo se puede crear personalización desde facturas de cliente."))
        if not self.partner_id:
            raise UserError(_("La factura no tiene cliente."))
        personalization = self.env["sp.personalization.order"].create({
            "account_move_id": self.id,
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
        })
        personalization.create_groups_from_account_move(self)
        self.message_post(body=_("Ficha de personalización creada: %s") % personalization.name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Ficha de personalización"),
            "res_model": "sp.personalization.order",
            "view_mode": "form",
            "res_id": personalization.id,
            "target": "current",
        }

    def action_view_personalization_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Fichas de personalización"),
            "res_model": "sp.personalization.order",
            "view_mode": "list,form",
            "domain": [("account_move_id", "=", self.id)],
            "context": {"default_account_move_id": self.id, "default_partner_id": self.partner_id.id, "default_company_id": self.company_id.id},
        }
