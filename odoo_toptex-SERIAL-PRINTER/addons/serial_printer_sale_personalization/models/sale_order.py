# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    personalization_order_ids = fields.One2many("sp.personalization.order", "sale_order_id", string="Fichas personalización")
    personalization_count = fields.Integer(compute="_compute_personalization_count")
    sp_has_textile_personalization_lines = fields.Boolean(compute="_compute_sp_has_textile_personalization_lines")
    sp_personalization_portal_url = fields.Char(compute="_compute_sp_personalization_portal_url")

    @api.depends("personalization_order_ids")
    def _compute_personalization_count(self):
        for order in self:
            order.personalization_count = len(order.personalization_order_ids)

    def _is_personalization_line_candidate(self, line):
        if not line.product_uom_qty or line.display_type:
            return False
        description = (line.name or "").strip().lower()
        if any(item in description for item in ["entrega estándar", "standard delivery", "envío", "shipping", "delivery"]):
            return False
        product = line.product_id
        if product and "detailed_type" in product._fields and product.detailed_type == "service":
            return False
        return bool(product or description)

    @api.depends("order_line.name", "order_line.product_uom_qty", "order_line.display_type", "order_line.product_id")
    def _compute_sp_has_textile_personalization_lines(self):
        for order in self:
            order.sp_has_textile_personalization_lines = any(order._is_personalization_line_candidate(line) for line in order.order_line)

    @api.depends("access_token")
    def _compute_sp_personalization_portal_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for order in self:
            order.sp_personalization_portal_url = "%s/personalizacion/presupuesto/%s?access_token=%s" % (
                base_url.rstrip("/"),
                order.id,
                order.access_token or "",
            )

    def _get_or_create_personalization_order(self):
        self.ensure_one()
        personalization = self.personalization_order_ids[:1]
        if personalization:
            personalization._ensure_groups_from_source()
            return personalization
        if not self.partner_id:
            raise UserError(_("El presupuesto no tiene cliente."))
        personalization = self.env["sp.personalization.order"].create({
            "sale_order_id": self.id,
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
        })
        personalization.create_groups_from_sale_order(self)
        self.message_post(body=_("Ficha de personalización creada: %s") % personalization.name)
        return personalization

    def action_create_personalization_order(self):
        self.ensure_one()
        personalization = self._get_or_create_personalization_order()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ficha de personalización"),
            "res_model": "sp.personalization.order",
            "view_mode": "form",
            "res_id": personalization.id,
            "target": "current",
        }

    def action_open_personalization_portal(self):
        self.ensure_one()
        personalization = self._get_or_create_personalization_order()
        return {"type": "ir.actions.act_url", "url": personalization.portal_url, "target": "new"}

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
