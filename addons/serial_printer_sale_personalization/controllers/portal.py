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

    def _save_visible_markings(self, personalization, post):
        """Save every marking currently rendered in the public form.
        Field names are prefixed with marking_<id>_... so one normal POST can save
        the whole page without AJAX and without separate nested forms.
        """
        Marking = request.env["sp.personalization.marking"].sudo()
        for marking in personalization.group_ids.mapped("marking_ids"):
            marker_prefix = "marking_%s_" % marking.id
            # Only save markings that were present in the submitted page.
            if (marker_prefix + "name") not in post and (marker_prefix + "position") not in post:
                continue

            vals = {
                "name": post.get(marker_prefix + "name") or marking.name,
                "technique": self._selection_value("sp.personalization.marking", "technique", post.get(marker_prefix + "technique"), marking.technique),
                "position": self._selection_value("sp.personalization.marking", "position", post.get(marker_prefix + "position"), marking.position),
                "print_color": self._selection_value("sp.personalization.marking", "print_color", post.get(marker_prefix + "print_color"), marking.print_color),
                "size_mode": self._selection_value("sp.personalization.marking", "size_mode", post.get(marker_prefix + "size_mode"), marking.size_mode),
                "width_cm": self._to_float(post.get(marker_prefix + "width_cm")),
                "height_cm": self._to_float(post.get(marker_prefix + "height_cm")),
                "notes": post.get(marker_prefix + "notes") or "",
            }
            marking.write(vals)

            for size_line in marking.size_ids:
                key = "size_qty_%s" % size_line.id
                if key in post:
                    size_line.sudo().write({"qty": self._to_float(post.get(key))})

            for placement in marking.placement_ids:
                production_file = request.httprequest.files.get("production_%s" % placement.id)
                preview_file = request.httprequest.files.get("preview_%s" % placement.id)
                if production_file and getattr(production_file, "filename", False):
                    placement.create_attachment_from_upload(production_file, "production_attachment_id")
                if preview_file and getattr(preview_file, "filename", False):
                    placement.create_attachment_from_upload(preview_file, "preview_attachment_id")
        return True

    def _handle_group_action(self, personalization, group_action):
        if not group_action or ":" not in group_action:
            return False
        action_name, group_id_text = group_action.split(":", 1)
        group = request.env["sp.personalization.group"].sudo().browse(self._to_int(group_id_text)).exists()
        if not group or group.personalization_id.id != personalization.id:
            return False
        if action_name == "add_marking":
            group.action_add_marking()
        elif action_name == "personalize_group":
            group.action_personalize()
        elif action_name == "split_two":
            group.action_split_two_markings()
        elif action_name == "mark_no":
            group.action_mark_no_personalization()
        elif action_name == "split_group" and not group.marking_ids:
            group.action_split_by_sale_lines()
        return True

    @http.route(["/personalizacion/<string:access_token>"], type="http", auth="public", website=True, csrf=True, methods=["GET", "POST"])
    def personalization_form(self, access_token, **post):
        personalization = self._get_personalization(access_token)
        if not personalization:
            return request.not_found()

        if request.httprequest.method == "POST":
            action = post.get("action")
            group_action = post.get("group_action")

            # First save all visible marking data submitted by the page. This is the
            # key fix: final send and every button persist the personalization before
            # redirecting, registering, notifying, or generating the PDF later.
            self._save_visible_markings(personalization, post)

            if group_action:
                self._handle_group_action(personalization, group_action)
            elif action == "save_all":
                personalization.message_post(body="Ficha de personalización guardada desde el formulario cliente.")
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
