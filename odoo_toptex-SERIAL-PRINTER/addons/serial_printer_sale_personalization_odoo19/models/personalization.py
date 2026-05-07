# -*- coding: utf-8 -*-
import base64
import re
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

PRINT_COLOR_SELECTION = [
    ("white", "Blanco"), ("black", "Negro"), ("light_grey", "Gris claro"),
    ("medium_grey", "Gris medio"), ("dark_grey", "Gris oscuro"),
    ("navy", "Marino"), ("royal_blue", "Azul royal"), ("sky_blue", "Azul cielo"),
    ("red", "Rojo"), ("burgundy", "Burdeos"), ("yellow", "Amarillo"),
    ("orange", "Naranja"), ("bottle_green", "Verde botella"), ("green", "Verde"),
    ("brown", "Marrón"), ("chocolate", "Chocolate"),
    ("baby_pink", "Rosa bebé"), ("dusty_pink", "Rosa empolvado"),
    ("nude_pink", "Rosa nude"), ("pastel_coral", "Coral pastel"),
    ("peach", "Melocotón"), ("apricot", "Albaricoque"),
    ("soft_salmon", "Salmón suave"), ("vanilla", "Vainilla"),
    ("butter_yellow", "Amarillo mantequilla"), ("cream", "Crema"),
    ("pistachio", "Pistacho"), ("pastel_green", "Verde pastel"),
    ("water_green", "Verde agua"), ("mint", "Menta"), ("soft_mint", "Menta suave"),
    ("sage", "Salvia"), ("eucalyptus", "Eucalipto"), ("pastel_aqua", "Aqua pastel"),
    ("baby_blue", "Azul bebé"), ("powder_blue", "Azul polvo"),
    ("pastel_blue", "Azul pastel"), ("lavender", "Lavanda"),
    ("pastel_lilac", "Lila pastel"), ("mauve", "Malva"),
    ("soft_purple", "Morado suave"), ("pearl", "Perla"), ("sand", "Arena"),
    ("light_beige", "Beige claro"), ("pink_beige", "Beige rosado"),
    ("soft_taupe", "Taupe suave"), ("light_camel", "Camel claro"),
]

PRINT_COLOR_HEX = {
    "white": "#FFFFFF", "black": "#111111", "light_grey": "#D9D9D9",
    "medium_grey": "#A3A3A3", "dark_grey": "#555555", "navy": "#14213D",
    "royal_blue": "#1D4ED8", "sky_blue": "#BAE6FD", "red": "#DC2626",
    "burgundy": "#7F1D1D", "yellow": "#FACC15", "orange": "#F97316",
    "bottle_green": "#14532D", "green": "#22C55E", "brown": "#7C4A2D",
    "chocolate": "#3F2417", "baby_pink": "#FBCFE8", "dusty_pink": "#F9A8D4",
    "nude_pink": "#F4C2C2", "pastel_coral": "#FCA5A5", "peach": "#FED7AA",
    "apricot": "#FDBA74", "soft_salmon": "#F9B4AB", "vanilla": "#FEF3C7",
    "butter_yellow": "#FDE68A", "cream": "#FFF7D6", "pistachio": "#D9F99D",
    "pastel_green": "#BBF7D0", "water_green": "#A7F3D0", "mint": "#CCFBF1",
    "soft_mint": "#D1FAE5", "sage": "#A7B7A5", "eucalyptus": "#B7C9B2",
    "pastel_aqua": "#CFFAFE", "baby_blue": "#BFDBFE", "powder_blue": "#C7D2FE",
    "pastel_blue": "#DBEAFE", "lavender": "#DDD6FE", "pastel_lilac": "#E9D5FF",
    "mauve": "#D8B4FE", "soft_purple": "#C4B5FD", "pearl": "#F5F5F4",
    "sand": "#D6C3A3", "light_beige": "#E7D7C9", "pink_beige": "#E9CFC5",
    "soft_taupe": "#CBB8A8", "light_camel": "#D2B48C",
}

TECHNIQUE_SELECTION = [
    ("screen", "Serigrafía"), ("embroidery", "Bordado"), ("dtf", "DTF"), ("to_advise", "A recomendar"),
]

POSITION_SELECTION = [
    ("front_left", "Pecho izquierdo"), ("front_center", "Pecho centro"), ("back", "Espalda"),
    ("front_back", "Pecho + espalda"), ("neck", "Cuello / etiqueta"),
    ("front_back_neck", "Pecho + espalda + cuello"), ("right_sleeve", "Manga derecha"),
    ("left_sleeve", "Manga izquierda"), ("cap_front", "Frontal gorra"),
    ("cap_side", "Lateral gorra"), ("cap_front_side", "Frontal + lateral gorra"),
]

SIZE_MODE_SELECTION = [
    ("proportional", "A proporción"), ("small", "Pequeño"), ("medium", "Medio"),
    ("large", "Grande"), ("exact", "Medida exacta"),
]

GROUP_STATUS_SELECTION = [
    ("pending", "Pendiente"),
    ("yes", "Personalizar"),
    ("no", "No personalizar"),
]

SIZE_NAMES = {"xxs", "xs", "s", "m", "l", "xl", "xxl", "xxxl", "2xl", "3xl", "4xl", "5xl"}


def _norm(value):
    return (value or "").strip().lower()


def _format_qty(qty):
    return int(qty) if float(qty).is_integer() else qty


def _clean_text(value):
    return re.sub(r"\s+", " ", (value or "").replace("\xa0", " ")).strip()


def _short_ref(value):
    value = _clean_text(value)
    return value.split("_", 1)[0] if "_" in value else value


def _split_qty_map(size_map):
    first = {}
    second = {}
    for size, qty in size_map.items():
        half = int((qty or 0) // 2)
        first[size] = half
        second[size] = max(0, (qty or 0) - half)
    return first, second


class SpPersonalizationOrder(models.Model):
    _name = "sp.personalization.order"
    _description = "Serial Printer Personalization"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="Nuevo", copy=False, tracking=True)
    sale_order_id = fields.Many2one("sale.order", string="Presupuesto/Pedido", ondelete="set null")
    account_move_id = fields.Many2one("account.move", string="Factura", ondelete="set null")
    partner_id = fields.Many2one("res.partner", string="Cliente", required=True, tracking=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    access_token = fields.Char(default=lambda self: uuid.uuid4().hex, copy=False, index=True)
    state = fields.Selection([
        ("draft", "Borrador"), ("sent", "Enviado"), ("customer_done", "Cliente completó"),
        ("reviewed", "Revisado"), ("production", "Producción"), ("done", "Finalizado"),
        ("cancel", "Cancelado"),
    ], default="draft", tracking=True)
    group_ids = fields.One2many("sp.personalization.group", "personalization_id", string="Grupos")
    customer_notes = fields.Text(string="Notas cliente")
    internal_notes = fields.Text(string="Notas internas")
    confirmed_date = fields.Datetime(string="Fecha confirmación")
    portal_url = fields.Char(compute="_compute_portal_url")
    source_display_name = fields.Char(compute="_compute_source_display_name")
    group_count = fields.Integer(compute="_compute_counts")
    marking_count = fields.Integer(compute="_compute_counts")

    _sql_constraints = [
        ("access_token_unique", "unique(access_token)", "El token de acceso debe ser único."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("sp.personalization.order") or "Nuevo"
        records = super().create(vals_list)
        records._ensure_groups_from_source()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "sale_order_id" in vals or "account_move_id" in vals:
            self._ensure_groups_from_source()
        return res

    @api.depends("group_ids", "group_ids.marking_ids")
    def _compute_counts(self):
        for rec in self:
            rec.group_count = len(rec.group_ids)
            rec.marking_count = sum(len(group.marking_ids) for group in rec.group_ids)

    @api.depends("sale_order_id.name", "account_move_id.name")
    def _compute_source_display_name(self):
        for rec in self:
            rec.source_display_name = rec.sale_order_id.name or rec.account_move_id.name or ""

    @api.depends("access_token")
    def _compute_portal_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for rec in self:
            rec.portal_url = "%s/personalizacion/%s" % (base_url.rstrip("/"), rec.access_token or "")

    def action_open_portal(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self.portal_url, "target": "new"}

    def action_send_to_customer(self):
        for rec in self:
            rec.state = "sent"
            rec.message_post(body=_("Formulario de personalización: %s") % rec.portal_url)
        return True

    def action_mark_reviewed(self):
        self.write({"state": "reviewed"})
        return True

    def action_mark_production(self):
        self.write({"state": "production"})
        return True

    def action_mark_done(self):
        self.write({"state": "done"})
        return True

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref("serial_printer_sale_personalization.action_report_sp_personalization").report_action(self)

    def _ensure_groups_from_source(self):
        for rec in self:
            if rec.group_ids:
                continue
            if rec.sale_order_id:
                rec.create_groups_from_sale_order(rec.sale_order_id)
            elif rec.account_move_id:
                rec.create_groups_from_account_move(rec.account_move_id)
        return True

    def action_regenerate_groups_from_source(self):
        for rec in self:
            if not rec.sale_order_id and not rec.account_move_id:
                raise UserError(_("Selecciona primero un presupuesto o una factura."))
            if rec.marking_count:
                raise UserError(_("No se pueden regenerar líneas porque ya hay marcajes. Elimina los marcajes si quieres volver a cargar desde el origen."))
            if rec.sale_order_id:
                rec.create_groups_from_sale_order(rec.sale_order_id)
            else:
                rec.create_groups_from_account_move(rec.account_move_id)
            rec.message_post(body=_("Se han regenerado los grupos de producto desde el documento origen."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Personalización"),
                "message": _("Líneas cargadas desde el presupuesto/factura."),
                "type": "success",
                "sticky": False,
            },
        }

    def _get_product_color_size(self, product):
        color = "Sin color"
        size = "Sin talla"
        if not product:
            return color, size
        for value in product.product_template_attribute_value_ids:
            attr = _norm(value.attribute_id.name)
            if "color" in attr or "colour" in attr:
                color = value.name or color
            elif "talla" in attr or "size" in attr:
                size = value.name or size
        return color, size

    def _parse_line_description(self, description):
        text = _clean_text(description).replace(" Descargar PNG", "").strip()
        ref = ""
        code_match = re.match(r"^\[([^\]]+)\]\s*(.*)$", text)
        if code_match:
            ref = code_match.group(1)
            text = code_match.group(2).strip()

        color = ""
        size = ""
        variant_match = re.search(r"\(([^()]*)\)\s*$", text)
        if variant_match:
            variant_parts = [_clean_text(part) for part in variant_match.group(1).split(",") if _clean_text(part)]
            text = text[:variant_match.start()].strip()
            if len(variant_parts) >= 2:
                color = ", ".join(variant_parts[:-1])
                size = variant_parts[-1]
            elif len(variant_parts) == 1:
                value = variant_parts[0]
                if _norm(value) in SIZE_NAMES:
                    size = value
                else:
                    color = value
        return {
            "product_ref": ref,
            "product_name": text,
            "color_name": color,
            "size_name": size,
        }

    def _should_use_line(self, line, qty):
        if not qty or line.display_type:
            return False
        description = _norm(line.name)
        ignored_text = ["entrega estándar", "standard delivery", "envío", "shipping", "delivery"]
        if any(item in description for item in ignored_text):
            return False
        product = line.product_id
        if product and "detailed_type" in product._fields and product.detailed_type == "service":
            return False
        return bool(product or description)

    def _line_summary(self, line, product, color, size, qty):
        ref = product.default_code or product.product_tmpl_id.default_code if product else ""
        parsed = self._parse_line_description(line.name if line else "")
        ref = _short_ref(parsed["product_ref"]) or ref
        label = parsed["product_name"] or (product.product_tmpl_id.display_name if product else _clean_text(line.name if line else ""))
        details = " / ".join(item for item in [ref, color if color != "Sin color" else "", size if size != "Sin talla" else ""] if item)
        return "%s%s - %s uds" % (label, " (%s)" % details if details else "", _format_qty(qty))

    def _group_line(self, grouped, product, qty, source_line=False):
        if not qty:
            return
        parsed = self._parse_line_description(source_line.name if source_line else "")
        color, size = self._get_product_color_size(product)
        if color == "Sin color" and parsed["color_name"]:
            color = parsed["color_name"]
        if size == "Sin talla" and parsed["size_name"]:
            size = parsed["size_name"]
        product_name = parsed["product_name"] or (product.product_tmpl_id.display_name if product else "Producto sin nombre")
        product_ref = _short_ref(parsed["product_ref"]) or ((product.default_code or product.product_tmpl_id.default_code) if product else "")
        key = (_norm(product_name) or (product.product_tmpl_id.id if product else product_ref), color)
        if key not in grouped:
            grouped[key] = {
                "product_tmpl_id": product.product_tmpl_id.id if product else False,
                "product_id": product.id if product else False,
                "product_name": product_name,
                "product_ref": product_ref or "",
                "color_name": color,
                "qty_total": 0.0,
                "sizes": {},
                "line_ids": [],
                "line_summaries": [],
                "product_image_1920": (product.image_1920 or product.product_tmpl_id.image_1920) if product else False,
            }
        grouped[key]["qty_total"] += qty
        grouped[key]["sizes"][size] = grouped[key]["sizes"].get(size, 0.0) + qty
        grouped[key]["line_summaries"].append(self._line_summary(source_line, product, color, size, qty))
        if source_line and source_line._name == "sale.order.line":
            grouped[key]["line_ids"].append(source_line.id)

    def _create_group_records(self, grouped, line_model):
        for data in grouped.values():
            size_summary = " · ".join("%s: %s" % (size, _format_qty(qty)) for size, qty in sorted(data["sizes"].items()))
            vals = {
                "personalization_id": self.id,
                "product_tmpl_id": data["product_tmpl_id"],
                "product_id": data["product_id"],
                "product_name": data["product_name"],
                "product_ref": data["product_ref"],
                "color_name": data["color_name"],
                "qty_total": data["qty_total"],
                "size_summary": size_summary,
                "original_line_summary": "\n".join(data["line_summaries"]),
                "product_image_1920": data["product_image_1920"],
            }
            if line_model == "sale" and data["line_ids"]:
                vals["sale_line_ids"] = [(6, 0, data["line_ids"])]
            self.env["sp.personalization.group"].create(vals)

    def create_groups_from_sale_order(self, sale_order):
        self.ensure_one()
        self.group_ids.unlink()
        grouped = {}
        for line in sale_order.order_line:
            if self._should_use_line(line, line.product_uom_qty):
                self._group_line(grouped, line.product_id, line.product_uom_qty, line)
        self._create_group_records(grouped, "sale")

    def create_groups_from_account_move(self, move):
        self.ensure_one()
        self.group_ids.unlink()
        grouped = {}
        for line in move.invoice_line_ids:
            if self._should_use_line(line, line.quantity):
                self._group_line(grouped, line.product_id, line.quantity, line)
        self._create_group_records(grouped, "invoice")


class SpPersonalizationGroup(models.Model):
    _name = "sp.personalization.group"
    _description = "Personalization Product Group"
    _order = "id asc"

    personalization_id = fields.Many2one("sp.personalization.order", required=True, ondelete="cascade")
    product_tmpl_id = fields.Many2one("product.template")
    product_id = fields.Many2one("product.product")
    product_name = fields.Char()
    product_ref = fields.Char()
    color_name = fields.Char()
    qty_total = fields.Float()
    size_summary = fields.Char()
    original_line_summary = fields.Text()
    product_image_1920 = fields.Image(max_width=1920, max_height=1920)
    sale_line_ids = fields.Many2many("sale.order.line", string="Líneas presupuesto")
    sale_line_count = fields.Integer(compute="_compute_sale_line_count")
    status = fields.Selection(GROUP_STATUS_SELECTION, default="pending")
    group_type = fields.Selection([("shirt", "Textil"), ("cap", "Gorra")], compute="_compute_group_type")
    garment_color_key = fields.Char(compute="_compute_garment_color_key")
    qty_status_ok = fields.Boolean(compute="_compute_qty_status")
    qty_status_text = fields.Char(compute="_compute_qty_status")
    marking_ids = fields.One2many("sp.personalization.marking", "group_id", string="Marcajes")

    @api.depends("sale_line_ids")
    def _compute_sale_line_count(self):
        for group in self:
            group.sale_line_count = len(group.sale_line_ids)

    @api.depends("product_name", "product_ref")
    def _compute_group_type(self):
        for group in self:
            group.group_type = "cap" if group.is_cap() else "shirt"

    @api.depends("color_name")
    def _compute_garment_color_key(self):
        for group in self:
            color = _norm(group.color_name)
            if "black" in color or "negro" in color:
                group.garment_color_key = "black"
            elif "navy" in color or "marino" in color or "indigo" in color:
                group.garment_color_key = "navy"
            elif "beige" in color or "camel" in color or "khaki" in color:
                group.garment_color_key = "beige"
            elif "/" in color or "tricolor" in color:
                group.garment_color_key = "tricolor"
            else:
                group.garment_color_key = "default"

    @api.depends("marking_ids.size_ids.qty", "size_summary", "status")
    def _compute_qty_status(self):
        for group in self:
            if group.status == "no":
                group.qty_status_ok = True
                group.qty_status_text = _("No personalizar")
                continue
            if not group.marking_ids:
                group.qty_status_ok = False
                group.qty_status_text = _("Sin marcajes")
                continue
            total_map = group._get_size_map()
            used = {size: 0.0 for size in total_map}
            for marking in group.marking_ids:
                for size_line in marking.size_ids:
                    used[size_line.size_name] = used.get(size_line.size_name, 0.0) + size_line.qty
            problems = []
            for size, total in total_map.items():
                diff = used.get(size, 0.0) - total
                if diff < 0:
                    problems.append(_("%s: faltan %s") % (size, _format_qty(abs(diff))))
                elif diff > 0:
                    problems.append(_("%s: sobran %s") % (size, _format_qty(diff)))
            group.qty_status_ok = not problems
            group.qty_status_text = (
                _("Tallas correctas: %s/%s uds") % (_format_qty(sum(used.values())), _format_qty(group.qty_total))
                if not problems
                else " · ".join(problems)
            )

    def is_cap(self):
        self.ensure_one()
        text = _norm("%s %s" % (self.product_name, self.product_ref))
        return "gorra" in text or "cap" in text or text.startswith("kp")

    def _get_size_map(self):
        self.ensure_one()
        result = {}
        for part in (self.size_summary or "").split("·"):
            if ":" not in part:
                continue
            size, qty = part.split(":", 1)
            try:
                result[size.strip()] = float(qty.strip().replace(",", "."))
            except Exception:
                result[size.strip()] = 0.0
        return result

    def _set_marking_sizes(self, marking, size_map):
        marking.size_ids.unlink()
        for size, qty in size_map.items():
            self.env["sp.personalization.size"].create({
                "marking_id": marking.id,
                "size_name": size,
                "qty": qty,
            })

    def _create_default_marking(self, name=False, size_map=False, position=False):
        self.ensure_one()
        self.status = "yes"
        position = position or ("cap_front" if self.is_cap() else "front_left")
        technique = "embroidery" if self.is_cap() else "screen"
        color = "white" if _norm(self.color_name) in ["black", "negro", "navy", "navy blue", "marino"] else "black"
        marking = self.env["sp.personalization.marking"].create({
            "group_id": self.id,
            "name": name or "Marcaje cliente",
            "position": position,
            "technique": technique,
            "print_color": color,
        })
        if size_map:
            self._set_marking_sizes(marking, size_map)
        marking.sync_placements()
        return marking

    def action_add_marking(self):
        for group in self:
            group._create_default_marking()
        return True

    def action_personalize(self):
        for group in self:
            group.status = "yes"
            if not group.marking_ids:
                group._create_default_marking()
        return True

    def action_mark_no_personalization(self):
        for group in self:
            group.marking_ids.unlink()
            group.status = "no"
        return True

    def action_split_two_markings(self):
        for group in self:
            if group.marking_ids:
                group.marking_ids.unlink()
            group.status = "yes"
            first_map, second_map = _split_qty_map(group._get_size_map())
            second_position = "cap_side" if group.is_cap() else "back"
            group._create_default_marking(name=_("Marcaje A"), size_map=first_map)
            group._create_default_marking(name=_("Marcaje B"), size_map=second_map, position=second_position)
        return True

    def action_split_by_sale_lines(self):
        self.ensure_one()
        if self.marking_ids:
            raise UserError(_("No se puede separar un grupo que ya tiene marcajes. Elimina o mueve los marcajes primero."))
        if len(self.sale_line_ids) <= 1:
            raise UserError(_("Este grupo no tiene varias líneas de presupuesto para separar."))

        personalization = self.personalization_id
        for line in self.sale_line_ids:
            grouped = {}
            personalization._group_line(grouped, line.product_id, line.product_uom_qty, line)
            personalization._create_group_records(grouped, "sale")
        self.unlink()
        return True


class SpPersonalizationMarking(models.Model):
    _name = "sp.personalization.marking"
    _description = "Personalization Marking"
    _order = "id asc"

    group_id = fields.Many2one("sp.personalization.group", required=True, ondelete="cascade")
    personalization_id = fields.Many2one(related="group_id.personalization_id", store=True)
    name = fields.Char(default="Marcaje cliente")
    technique = fields.Selection(TECHNIQUE_SELECTION, default="screen", required=True)
    position = fields.Selection(POSITION_SELECTION, default="front_left", required=True)
    print_color = fields.Selection(PRINT_COLOR_SELECTION, default="white", required=True)
    print_color_hex = fields.Char(compute="_compute_print_color_hex", store=True)
    size_mode = fields.Selection(SIZE_MODE_SELECTION, default="proportional")
    width_cm = fields.Float()
    height_cm = fields.Float()
    notes = fields.Text()
    size_ids = fields.One2many("sp.personalization.size", "marking_id", string="Tallas")
    placement_ids = fields.One2many("sp.personalization.placement", "marking_id", string="Ubicaciones")
    qty_total = fields.Float(compute="_compute_qty_total", store=True)

    @api.model
    def _get_print_color_hex_map(self):
        return PRINT_COLOR_HEX

    @api.constrains("width_cm", "height_cm")
    def _check_dimensions(self):
        for rec in self:
            if rec.width_cm < 0 or rec.height_cm < 0:
                raise ValidationError(_("Las medidas no pueden ser negativas."))

    @api.depends("print_color")
    def _compute_print_color_hex(self):
        for rec in self:
            rec.print_color_hex = PRINT_COLOR_HEX.get(rec.print_color or "black", "#111111")

    @api.depends("size_ids.qty")
    def _compute_qty_total(self):
        for rec in self:
            rec.qty_total = sum(rec.size_ids.mapped("qty"))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.create_default_sizes()
            rec.sync_placements()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "position" in vals:
            for rec in self:
                rec.sync_placements()
        return res

    def create_default_sizes(self):
        for rec in self:
            if rec.size_ids:
                continue
            for part in (rec.group_id.size_summary or "").split("·"):
                if ":" not in part:
                    continue
                size, qty = part.split(":", 1)
                try:
                    qty_float = float(qty.strip().replace(",", "."))
                except Exception:
                    qty_float = 0.0
                self.env["sp.personalization.size"].create({"marking_id": rec.id, "size_name": size.strip(), "qty": qty_float})

    def required_placements(self):
        self.ensure_one()
        mapping = {
            "front_left": [("front_left", "Pecho izq.", "front")],
            "front_center": [("front_center", "Pecho centro", "front")],
            "back": [("back", "Espalda", "back")],
            "front_back": [("front_left", "Pecho", "front"), ("back", "Espalda", "back")],
            "neck": [("neck", "Cuello / etiqueta", "back")],
            "front_back_neck": [("front_left", "Pecho", "front"), ("back", "Espalda", "back"), ("neck", "Cuello / etiqueta", "back")],
            "right_sleeve": [("right_sleeve", "Manga derecha", "front")],
            "left_sleeve": [("left_sleeve", "Manga izquierda", "front")],
            "cap_front": [("cap_front", "Frontal", "front")],
            "cap_side": [("cap_side", "Lateral", "side")],
            "cap_front_side": [("cap_front", "Frontal", "front"), ("cap_side", "Lateral", "side")],
        }
        return mapping.get(self.position, mapping["front_left"])

    def sync_placements(self):
        for rec in self:
            required = rec.required_placements()
            required_keys = [item[0] for item in required]
            rec.placement_ids.filtered(lambda p: p.placement_key not in required_keys).unlink()
            existing = {placement.placement_key: placement for placement in rec.placement_ids}
            for key, label, side in required:
                if key in existing:
                    existing[key].write({"placement_label": label, "side": side})
                else:
                    self.env["sp.personalization.placement"].create({"marking_id": rec.id, "placement_key": key, "placement_label": label, "side": side})


class SpPersonalizationSize(models.Model):
    _name = "sp.personalization.size"
    _description = "Personalization Size Split"
    _order = "id asc"

    marking_id = fields.Many2one("sp.personalization.marking", required=True, ondelete="cascade")
    size_name = fields.Char(required=True)
    qty = fields.Float(default=0.0)

    @api.constrains("qty")
    def _check_qty(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError(_("Las cantidades no pueden ser negativas."))


class SpPersonalizationPlacement(models.Model):
    _name = "sp.personalization.placement"
    _description = "Personalization Placement Files"
    _order = "id asc"

    marking_id = fields.Many2one("sp.personalization.marking", required=True, ondelete="cascade")
    group_id = fields.Many2one(related="marking_id.group_id", store=True)
    personalization_id = fields.Many2one(related="marking_id.personalization_id", store=True)
    placement_key = fields.Char(required=True)
    placement_label = fields.Char(required=True)
    side = fields.Selection([("front", "Delante"), ("back", "Espalda"), ("side", "Lateral")], default="front")
    production_attachment_id = fields.Many2one("ir.attachment")
    preview_attachment_id = fields.Many2one("ir.attachment")
    preview_image = fields.Image(max_width=1024, max_height=1024)
    production_filename = fields.Char(related="production_attachment_id.name", store=True)
    preview_filename = fields.Char(related="preview_attachment_id.name", store=True)

    def create_attachment_from_upload(self, upload_file, field_name):
        self.ensure_one()
        if not upload_file:
            return False
        content = upload_file.read()
        filename = upload_file.filename or "archivo"
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "datas": base64.b64encode(content),
            "res_model": self._name,
            "res_id": self.id,
            "type": "binary",
            "mimetype": upload_file.content_type or "application/octet-stream",
            "access_token": uuid.uuid4().hex,
        })
        self.write({field_name: attachment.id})
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if field_name == "preview_attachment_id" or ext in ["png", "jpg", "jpeg", "webp", "svg"]:
            self.preview_image = base64.b64encode(content)
        return attachment
