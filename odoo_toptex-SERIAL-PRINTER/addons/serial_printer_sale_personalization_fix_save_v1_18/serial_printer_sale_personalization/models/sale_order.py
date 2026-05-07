# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    personalization_order_ids = fields.One2many("sp.personalization.order", "sale_order_id", string="Fichas personalización")
    personalization_count = fields.Integer(compute="_compute_personalization_count")

    def _compute_personalization_count(self):
        for order in self:
            order.personalization_count = len(order.personalization_order_ids)

    def action_create_personalization_order(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("El presupuesto no tiene cliente."))
        personalization = self.env["sp.personalization.order"].create({
            "sale_order_id": self.id,
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
        })
        personalization.create_groups_from_sale_order(self)
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
            "domain": [("sale_order_id", "=", self.id)],
            "context": {"default_sale_order_id": self.id, "default_partner_id": self.partner_id.id, "default_company_id": self.company_id.id},
        }
