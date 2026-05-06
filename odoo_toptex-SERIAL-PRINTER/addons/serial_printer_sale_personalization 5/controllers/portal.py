# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


class SerialPrinterPersonalizationPortal(http.Controller):

    def _get_personalization(self, access_token):
        return request.env["sp.personalization.order"].sudo().search([("access_token", "=", access_token)], limit=1)

    @http.route(["/personalizacion/<string:access_token>"], type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def personalization_form(self, access_token, **post):
        personalization = self._get_personalization(access_token)
        if not personalization:
            return request.not_found()

        if request.httprequest.method == "POST":
            action = post.get("action")
            if action == "add_marking":
                group = request.env["sp.personalization.group"].sudo().browse(int(post.get("group_id") or 0))
                if group and group.personalization_id.id == personalization.id:
                    group.action_add_marking()
            elif action == "save_marking":
                marking = request.env["sp.personalization.marking"].sudo().browse(int(post.get("marking_id") or 0))
                if marking and marking.personalization_id.id == personalization.id:
                    marking.write({
                        "name": post.get("name") or marking.name,
                        "technique": post.get("technique") or marking.technique,
                        "position": post.get("position") or marking.position,
                        "print_color": post.get("print_color") or marking.print_color,
                        "size_mode": post.get("size_mode") or marking.size_mode,
                        "width_cm": float(post.get("width_cm") or 0.0),
                        "height_cm": float(post.get("height_cm") or 0.0),
                        "notes": post.get("notes") or "",
                    })
                    for size_line in marking.size_ids:
                        key = "size_qty_%s" % size_line.id
                        if key in post:
                            size_line.qty = float(post.get(key) or 0.0)
                    for placement in marking.placement_ids:
                        production_file = request.httprequest.files.get("production_%s" % placement.id)
                        preview_file = request.httprequest.files.get("preview_%s" % placement.id)
                        if production_file:
                            placement.create_attachment_from_upload(production_file, "production_attachment_id")
                        if preview_file:
                            placement.create_attachment_from_upload(preview_file, "preview_attachment_id")
            elif action == "confirm":
                personalization.write({
                    "state": "customer_done",
                    "confirmed_date": fields.Datetime.now(),
                    "customer_notes": post.get("customer_notes") or personalization.customer_notes,
                })
                personalization.message_post(body="Ficha de personalización enviada por el cliente.")
            return request.redirect("/personalizacion/%s" % access_token)

        Marking = request.env["sp.personalization.marking"].sudo()
        return request.render("serial_printer_sale_personalization.portal_personalization_form", {
            "personalization": personalization,
            "color_options": Marking._fields["print_color"].selection,
            "technique_options": Marking._fields["technique"].selection,
            "position_options": Marking._fields["position"].selection,
            "size_mode_options": Marking._fields["size_mode"].selection,
        })
