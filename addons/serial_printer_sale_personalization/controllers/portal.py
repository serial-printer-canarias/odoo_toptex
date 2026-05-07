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

    def _post_value(self, post, key, default=False):
        value = post.get(key)
        return default if value is None else value

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

    def _save_one_marking_from_post(self, marking, post, files):
        """Guarda un marcaje desde el formulario portal.

        Soporta los campos nuevos con prefijo marking_<id>_ y también los campos antiguos
        sin prefijo, para no romper compatibilidad si existe algún formulario viejo en caché.
        """
        self_marker = str(marking.id)
        generic = str(post.get("marking_id") or "") == self_marker
        prefix = "marking_%s_" % marking.id

        def field(name, default=False):
            prefixed_key = prefix + name
            if prefixed_key in post:
                return post.get(prefixed_key)
            if generic and name in post:
                return post.get(name)
            return default

        vals = {}
        name = field("name", None)
        if name is not None:
            vals["name"] = name or marking.name

        technique = field("technique", None)
        if technique is not None:
            vals["technique"] = self._selection_value("sp.personalization.marking", "technique", technique, marking.technique)

        position = field("position", None)
        if position is not None:
            vals["position"] = self._selection_value("sp.personalization.marking", "position", position, marking.position)

        print_color = field("print_color", None)
        if print_color is not None:
            vals["print_color"] = self._selection_value("sp.personalization.marking", "print_color", print_color, marking.print_color)

        size_mode = field("size_mode", None)
        if size_mode is not None:
            vals["size_mode"] = self._selection_value("sp.personalization.marking", "size_mode", size_mode, marking.size_mode)

        width_cm = field("width_cm", None)
        if width_cm is not None:
            vals["width_cm"] = self._to_float(width_cm)

        height_cm = field("height_cm", None)
        if height_cm is not None:
            vals["height_cm"] = self._to_float(height_cm)

        notes = field("notes", None)
        if notes is not None:
            vals["notes"] = notes or ""

        if vals:
            marking.write(vals)

        # Después de escribir position, el write() del modelo sincroniza las ubicaciones.
        for size_line in marking.size_ids:
            key = "size_qty_%s" % size_line.id
            if key in post:
                size_line.qty = self._to_float(post.get(key))

        for placement in marking.placement_ids:
            production_file = files.get("production_%s" % placement.id)
            preview_file = files.get("preview_%s" % placement.id)
            if production_file and getattr(production_file, "filename", None):
                placement.create_attachment_from_upload(production_file, "production_attachment_id")
            if preview_file and getattr(preview_file, "filename", None):
                placement.create_attachment_from_upload(preview_file, "preview_attachment_id")

    def _save_all_markings_from_post(self, personalization, post):
        files = request.httprequest.files
        for group in personalization.group_ids:
            for marking in group.marking_ids:
                self._save_one_marking_from_post(marking.sudo(), post, files)
        return True

    def _run_group_action(self, personalization, raw_value):
        if not raw_value or ":" not in raw_value:
            return False
        action, group_id = raw_value.split(":", 1)
        group = request.env["sp.personalization.group"].sudo().browse(self._to_int(group_id)).exists()
        if not group or group.personalization_id.id != personalization.id:
            return False
        if action == "add_marking":
            group.action_add_marking()
        elif action == "personalize_group":
            group.action_personalize()
        elif action == "split_two":
            group.action_split_two_markings()
        elif action == "mark_no":
            group.action_mark_no_personalization()
        elif action == "split_group" and not group.marking_ids:
            group.action_split_by_sale_lines()
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

            # Siempre guarda lo que haya en pantalla antes de cualquier acción.
            self._save_all_markings_from_post(personalization, post)

            group_action = post.get("group_action")
            if group_action:
                self._run_group_action(personalization, group_action)

            # Compatibilidad con formularios antiguos por si el navegador tiene caché.
            elif action in ("add_marking", "personalize_group", "split_two", "mark_no", "split_group"):
                group_id = post.get("group_id")
                self._run_group_action(personalization, "%s:%s" % (action, group_id))

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
