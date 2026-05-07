# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class SerialPrinterPersonalizationPortal(http.Controller):

    def _get_personalization(self, access_token):
        return request.env["sp.personalization.order"].sudo().search([("access_token", "=", access_token)], limit=1)

    def _to_float(self, value):
        try:
            return float(str(value or "0").replace(",", "."))
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

    def _form_values(self):
        return request.httprequest.form

    def _uploaded_file(self, field_name):
        upload = request.httprequest.files.get(field_name)
        if upload and getattr(upload, "filename", None):
            return upload
        return False

    def _save_all_visible_markings(self, personalization):
        """Guarda todos los marcajes presentes en el formulario actual.

        El portal usa un único POST para toda la página. Esto evita que el botón final
        confirme la ficha sin guardar primero técnica, posición, color, tallas, notas
        y archivos. La ruta usa token público, así que toda escritura se valida contra
        la ficha encontrada por access_token.
        """
        form = self._form_values()
        marking_ids = []
        for raw_id in form.getlist("marking_id"):
            marking_id = self._to_int(raw_id)
            if marking_id and marking_id not in marking_ids:
                marking_ids.append(marking_id)

        Marking = request.env["sp.personalization.marking"].sudo()
        for marking_id in marking_ids:
            marking = Marking.browse(marking_id).exists()
            if not marking or marking.personalization_id.id != personalization.id:
                continue

            values = {
                "name": form.get("name_%s" % marking.id) or marking.name,
                "technique": self._selection_value(
                    "sp.personalization.marking",
                    "technique",
                    form.get("technique_%s" % marking.id),
                    marking.technique,
                ),
                "position": self._selection_value(
                    "sp.personalization.marking",
                    "position",
                    form.get("position_%s" % marking.id),
                    marking.position,
                ),
                "print_color": self._selection_value(
                    "sp.personalization.marking",
                    "print_color",
                    form.get("print_color_%s" % marking.id),
                    marking.print_color,
                ),
                "size_mode": self._selection_value(
                    "sp.personalization.marking",
                    "size_mode",
                    form.get("size_mode_%s" % marking.id),
                    marking.size_mode,
                ),
                "width_cm": self._to_float(form.get("width_cm_%s" % marking.id)),
                "height_cm": self._to_float(form.get("height_cm_%s" % marking.id)),
                "notes": form.get("notes_%s" % marking.id) or "",
            }
            marking.write(values)

            for size_line in marking.size_ids:
                key = "size_qty_%s" % size_line.id
                if key in form:
                    size_line.sudo().write({"qty": self._to_float(form.get(key))})

            # Después de escribir position, sync_placements ya habrá creado/borrado
            # ubicaciones. Guardamos los archivos disponibles en el formulario.
            for placement in marking.placement_ids:
                production_file = self._uploaded_file("production_%s" % placement.id)
                preview_file = self._uploaded_file("preview_%s" % placement.id)
                if production_file:
                    placement.create_attachment_from_upload(production_file, "production_attachment_id")
                if preview_file:
                    placement.create_attachment_from_upload(preview_file, "preview_attachment_id")
        return True

    def _run_group_action(self, personalization, group_action):
        if not group_action or ":" not in group_action:
            return False
        action, raw_group_id = group_action.split(":", 1)
        group = request.env["sp.personalization.group"].sudo().browse(self._to_int(raw_group_id)).exists()
        if not group or group.personalization_id.id != personalization.id:
            return False
        if action == "personalize_group":
            group.action_personalize()
        elif action == "split_two":
            group.action_split_two_markings()
        elif action == "mark_no":
            group.action_mark_no_personalization()
        elif action == "add_marking":
            group.action_add_marking()
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

    @http.route(
        ["/personalizacion/<string:access_token>"],
        type="http",
        auth="public",
        website=True,
        csrf=False,
        methods=["GET", "POST"],
    )
    def personalization_form(self, access_token, **post):
        personalization = self._get_personalization(access_token)
        if not personalization:
            return request.not_found()

        if request.httprequest.method == "POST":
            # 1) Guardar siempre primero todo lo que esté visible en pantalla.
            self._save_all_visible_markings(personalization)

            # 2) Ejecutar acción puntual si el botón era de grupo.
            group_action = self._form_values().get("group_action")
            if group_action:
                self._run_group_action(personalization, group_action)

            # 3) Confirmar y notificar solo si el botón final fue Enviar ficha.
            action = self._form_values().get("action")
            if action == "confirm":
                personalization.action_customer_submit(self._form_values().get("customer_notes") or personalization.customer_notes)
            elif action == "save_all":
                if "customer_notes" in self._form_values():
                    personalization.customer_notes = self._form_values().get("customer_notes") or ""

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
