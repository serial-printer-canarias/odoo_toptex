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

    def _post_value(self, post, prefix, field_name, default=False):
        prefixed_key = "%s_%s" % (prefix, field_name)
        if prefixed_key in post:
            return post.get(prefixed_key)
        if field_name in post:
            return post.get(field_name)
        return default

    def _save_marking_from_post(self, marking, post, files, prefix=False):
        """Save one marking from the portal form.

        Supports both the old per-marking form names (name, technique, size_qty_ID)
        and the final single-form names (marking_ID_name, size_ID).
        """
        if not marking or not marking.exists():
            return False

        prefix = prefix or "marking_%s" % marking.id

        name = self._post_value(post, prefix, "name", marking.name)
        technique = self._post_value(post, prefix, "technique", marking.technique)
        position = self._post_value(post, prefix, "position", marking.position)
        print_color = self._post_value(post, prefix, "print_color", marking.print_color)
        size_mode = self._post_value(post, prefix, "size_mode", marking.size_mode)
        width_cm = self._post_value(post, prefix, "width_cm", marking.width_cm)
        height_cm = self._post_value(post, prefix, "height_cm", marking.height_cm)
        notes = self._post_value(post, prefix, "notes", marking.notes or "")

        marking.write({
            "name": name or marking.name,
            "technique": self._selection_value("sp.personalization.marking", "technique", technique, marking.technique),
            "position": self._selection_value("sp.personalization.marking", "position", position, marking.position),
            "print_color": self._selection_value("sp.personalization.marking", "print_color", print_color, marking.print_color),
            "size_mode": self._selection_value("sp.personalization.marking", "size_mode", size_mode, marking.size_mode),
            "width_cm": self._to_float(width_cm),
            "height_cm": self._to_float(height_cm),
            "notes": notes or "",
        })

        # Position write may create/remove placements. Work with the fresh recordset.
        marking.flush_recordset()

        for size_line in marking.size_ids:
            new_key = "size_%s" % size_line.id
            old_key = "size_qty_%s" % size_line.id
            if new_key in post:
                size_line.qty = self._to_float(post.get(new_key))
            elif old_key in post:
                size_line.qty = self._to_float(post.get(old_key))

        for placement in marking.placement_ids:
            production_file = files.get("production_%s" % placement.id)
            preview_file = files.get("preview_%s" % placement.id)
            if production_file and getattr(production_file, "filename", False):
                placement.create_attachment_from_upload(production_file, "production_attachment_id")
            if preview_file and getattr(preview_file, "filename", False):
                placement.create_attachment_from_upload(preview_file, "preview_attachment_id")

        return True

    def _save_all_markings_from_post(self, personalization, post):
        files = request.httprequest.files
        for marking in personalization.group_ids.mapped("marking_ids"):
            prefix = "marking_%s" % marking.id
            # In the final template every visible marking sends this hidden input.
            # If it is absent, keep backwards compatibility and still allow old save_marking.
            if ("%s_id" % prefix) in post or post.get("marking_id") == str(marking.id):
                self._save_marking_from_post(marking, post, files, prefix=prefix)
        return True

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

    @http.route(["/personalizacion/<string:access_token>"], type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def personalization_form(self, access_token, **post):
        personalization = self._get_personalization(access_token)
        if not personalization:
            return request.not_found()

        if request.httprequest.method == "POST":
            action = post.get("action")
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
                    self._save_marking_from_post(marking, post, request.httprequest.files, prefix="marking_%s" % marking.id)
            elif action == "save_all":
                self._save_all_markings_from_post(personalization, post)
            elif action == "confirm":
                self._save_all_markings_from_post(personalization, post)
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
