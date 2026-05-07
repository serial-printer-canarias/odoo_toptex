# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class SerialPrinterPersonalizationPortal(http.Controller):

    def _get_personalization(self, access_token):
        return request.env["sp.personalization.order"].sudo().search([("access_token", "=", access_token)], limit=1)

    def _to_float(self, value):
        try:
            return float((value or "0").replace(",", "."))
        except (TypeError, ValueError):
            return 0.0

    def _to_int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _selection_value(self, model, field_name, value, default):
        field = request.env[model]._fields[field_name]
        values = {key for key, _label in field.selection}
        return value if value in values else default

    def _image_response(self, image_data):
        if not image_data:
            return request.not_found()
        content = base64.b64decode(image_data)
        mimetype = "image/png"
        if content.startswith(b"\xff\xd8"):
            mimetype = "image/jpeg"
        elif content.startswith(b"RIFF") and b"WEBP" in content[:16]:
            mimetype = "image/webp"
        elif content.lstrip().startswith(b"<svg"):
            mimetype = "image/svg+xml"
        return request.make_response(
            content,
            headers=[
                ("Content-Type", mimetype),
                ("Cache-Control", "private, max-age=3600"),
            ],
        )

    @http.route(
        ["/personalizacion/<string:access_token>/grupo/<int:group_id>/imagen"],
        type="http",
        auth="public",
        website=True,
        csrf=False,
        methods=["GET"],
    )
    def personalization_group_image(self, access_token, group_id, **kwargs):
        personalization = self._get_personalization(access_token)
        group = personalization.group_ids.filtered(lambda item: item.id == group_id)[:1]
        if not personalization or not group:
            return request.not_found()
        return self._image_response(group.product_image_1920)

    @http.route(
        ["/personalizacion/<string:access_token>/ubicacion/<int:placement_id>/preview"],
        type="http",
        auth="public",
        website=True,
        csrf=False,
        methods=["GET"],
    )
    def personalization_placement_preview(self, access_token, placement_id, **kwargs):
        personalization = self._get_personalization(access_token)
        placement = request.env["sp.personalization.placement"].sudo().browse(placement_id).exists()
        if not personalization or not placement or placement.personalization_id.id != personalization.id:
            return request.not_found()
        attachment = placement.preview_attachment_id or placement.production_attachment_id
        if attachment and attachment.mimetype and attachment.mimetype.startswith("image/"):
            return request.make_response(
                base64.b64decode(attachment.datas or b""),
                headers=[
                    ("Content-Type", attachment.mimetype),
                    ("Cache-Control", "private, max-age=3600"),
                ],
            )
        return self._image_response(placement.preview_image)

    @http.route(
        ["/personalizacion/presupuesto/<int:order_id>"],
        type="http",
        auth="public",
        website=True,
        csrf=False,
        methods=["GET"],
    )
    def personalization_from_sale_order(self, order_id, access_token=None, **kwargs):
        order = request.env["sale.order"].sudo().browse(order_id).exists()
        if not order or not order.access_token or access_token != order.access_token:
            return request.not_found()
        personalization = order._get_or_create_personalization_order()
        return request.redirect("/personalizacion/%s" % personalization.access_token)


    def _save_all_markings_from_request(self, personalization, post):
        """Save every marking submitted by the portal final form.
        This avoids AJAX/fetch and prevents the page from hanging on public website submit.
        """
        form = request.httprequest.form
        marking_ids = form.getlist("marking_id")
        saved_any = False
        for marking_id in marking_ids:
            marking = request.env["sp.personalization.marking"].sudo().browse(self._to_int(marking_id)).exists()
            if not marking or marking.personalization_id.id != personalization.id:
                continue

            suffix = str(marking.id)
            values = {
                "name": post.get("name_%s" % suffix) or marking.name,
                "technique": self._selection_value("sp.personalization.marking", "technique", post.get("technique_%s" % suffix), marking.technique),
                "position": self._selection_value("sp.personalization.marking", "position", post.get("position_%s" % suffix), marking.position),
                "print_color": self._selection_value("sp.personalization.marking", "print_color", post.get("print_color_%s" % suffix), marking.print_color),
                "size_mode": self._selection_value("sp.personalization.marking", "size_mode", post.get("size_mode_%s" % suffix), marking.size_mode),
                "width_cm": self._to_float(post.get("width_cm_%s" % suffix)),
                "height_cm": self._to_float(post.get("height_cm_%s" % suffix)),
                "notes": post.get("notes_%s" % suffix) or "",
            }
            marking.write(values)

            for size_line in marking.size_ids:
                key = "size_qty_%s" % size_line.id
                if key in post:
                    size_line.sudo().qty = self._to_float(post.get(key))

            for placement in marking.placement_ids:
                production_file = request.httprequest.files.get("production_%s" % placement.id)
                preview_file = request.httprequest.files.get("preview_%s" % placement.id)
                if production_file and getattr(production_file, "filename", None):
                    placement.sudo().create_attachment_from_upload(production_file, "production_attachment_id")
                if preview_file and getattr(preview_file, "filename", None):
                    placement.sudo().create_attachment_from_upload(preview_file, "preview_attachment_id")
            saved_any = True
        return saved_any

    @http.route(["/personalizacion/<string:access_token>"], type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def personalization_form(self, access_token, **post):
        personalization = self._get_personalization(access_token)
        if not personalization:
            return request.not_found()

        if request.httprequest.method == "POST":
            action = post.get("action")
            if action in ("save_all", "confirm_all"):
                self._save_all_markings_from_request(personalization, post)
                if action == "confirm_all":
                    personalization.action_customer_submit(post.get("customer_notes") or personalization.customer_notes)
                return request.redirect("/personalizacion/%s" % access_token)
            if action == "add_marking":
                group = request.env["sp.personalization.group"].sudo().browse(self._to_int(post.get("group_id"))).exists()
                if group and group.personalization_id.id == personalization.id:
                    group.action_add_marking()
            elif action == "personalize_group":
                group = request.env["sp.personalization.group"].sudo().browse(self._to_int(post.get("group_id"))).exists()
                if group and group.personalization_id.id == personalization.id:
                    group.action_personalize()
            elif action == "split_two":
                group = request.env["sp.personalization.group"].sudo().browse(self._to_int(post.get("group_id"))).exists()
                if group and group.personalization_id.id == personalization.id:
                    group.action_split_two_markings()
            elif action == "mark_no":
                group = request.env["sp.personalization.group"].sudo().browse(self._to_int(post.get("group_id"))).exists()
                if group and group.personalization_id.id == personalization.id:
                    group.action_mark_no_personalization()
            elif action == "split_group":
                group = request.env["sp.personalization.group"].sudo().browse(self._to_int(post.get("group_id"))).exists()
                if group and group.personalization_id.id == personalization.id and not group.marking_ids:
                    group.action_split_by_sale_lines()
            elif action == "save_marking":
                marking = request.env["sp.personalization.marking"].sudo().browse(self._to_int(post.get("marking_id"))).exists()
                if marking and marking.personalization_id.id == personalization.id:
                    marking.write({
                        "name": post.get("name") or marking.name,
                        "technique": self._selection_value("sp.personalization.marking", "technique", post.get("technique"), marking.technique),
                        "position": self._selection_value("sp.personalization.marking", "position", post.get("position"), marking.position),
                        "print_color": self._selection_value("sp.personalization.marking", "print_color", post.get("print_color"), marking.print_color),
                        "size_mode": self._selection_value("sp.personalization.marking", "size_mode", post.get("size_mode"), marking.size_mode),
                        "width_cm": self._to_float(post.get("width_cm")),
                        "height_cm": self._to_float(post.get("height_cm")),
                        "notes": post.get("notes") or "",
                    })
                    for size_line in marking.size_ids:
                        key = "size_qty_%s" % size_line.id
                        if key in post:
                            size_line.qty = self._to_float(post.get(key))
                    for placement in marking.placement_ids:
                        production_file = request.httprequest.files.get("production_%s" % placement.id)
                        preview_file = request.httprequest.files.get("preview_%s" % placement.id)
                        if production_file:
                            placement.create_attachment_from_upload(production_file, "production_attachment_id")
                        if preview_file:
                            placement.create_attachment_from_upload(preview_file, "preview_attachment_id")
            elif action == "confirm":
                personalization.action_customer_submit(post.get("customer_notes") or personalization.customer_notes)
            return request.redirect("/personalizacion/%s" % access_token)

        personalization._ensure_groups_from_source()
        Marking = request.env["sp.personalization.marking"].sudo()
        return request.render("serial_printer_sale_personalization.portal_personalization_form", {
            "personalization": personalization,
            "color_options": Marking._fields["print_color"].selection,
            "technique_options": Marking._fields["technique"].selection,
            "position_options": Marking._fields["position"].selection,
            "size_mode_options": Marking._fields["size_mode"].selection,
            "color_hex_map": request.env["sp.personalization.marking"].sudo()._get_print_color_hex_map(),
        })
