# -*- coding: utf-8 -*-
import base64
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError

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


def _norm(value):
    return (value or "").strip().lower()


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
    group_count = fields.Integer(compute="_compute_counts")
    marking_count = fields.Integer(compute="_compute_counts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("sp.personalization.order") or "Nuevo"
        return super().create(vals_list)

    @api.depends("group_ids", "group_ids.marking_ids")
    def _compute_counts(self):
        for rec in self:
            rec.group_count = len(rec.group_ids)
            rec.marking_count = sum(len(group.marking_ids) for group in rec.group_ids)

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

    def _get_product_color_size(self, product):
        color = "Sin color"
        size = "Sin talla"
        for value in product.product_template_attribute_value_ids:
            attr = _norm(value.attribute_id.name)
            if "color" in attr or "colour" in attr:
                color = value.name or color
            elif "talla" in attr or "size" in attr:
                size = value.name or size
        return color, size

    def _group_line(self, grouped, product, qty, source_line=False):
        color, size = self._get_product_color_size(product)
        key = (product.product_tmpl_id.id, color)
        if key not in grouped:
            grouped[key] = {
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_id": product.id,
                "product_name": product.product_tmpl_id.display_name,
                "product_ref": product.default_code or product.product_tmpl_id.default_code or "",
                "color_name": color,
                "qty_total": 0.0,
                "sizes": {},
                "line_ids": [],
                "product_image_1920": product.image_1920 or product.product_tmpl_id.image_1920,
            }
        grouped[key]["qty_total"] += qty
        grouped[key]["sizes"][size] = grouped[key]["sizes"].get(size, 0.0) + qty
        if source_line:
            grouped[key]["line_ids"].append(source_line.id)

    def _create_group_records(self, grouped, line_model):
        for data in grouped.values():
            size_summary = " · ".join("%s: %s" % (size, int(qty) if float(qty).is_integer() else qty) for size, qty in sorted(data["sizes"].items()))
            vals = {
                "personalization_id": self.id,
                "product_tmpl_id": data["product_tmpl_id"],
                "product_id": data["product_id"],
                "product_name": data["product_name"],
                "product_ref": data["product_ref"],
                "color_name": data["color_name"],
                "qty_total": data["qty_total"],
                "size_summary": size_summary,
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
            if not line.display_type and line.product_id:
                self._group_line(grouped, line.product_id, line.product_uom_qty, line)
        self._create_group_records(grouped, "sale")

    def create_groups_from_account_move(self, move):
        self.ensure_one()
        self.group_ids.unlink()
        grouped = {}
        for line in move.invoice_line_ids:
            if not line.display_type and line.product_id:
                self._group_line(grouped, line.product_id, line.quantity, False)
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
    product_image_1920 = fields.Image(max_width=1920, max_height=1920)
    sale_line_ids = fields.Many2many("sale.order.line", string="Líneas presupuesto")
    marking_ids = fields.One2many("sp.personalization.marking", "group_id", string="Marcajes")

    def is_cap(self):
        self.ensure_one()
        text = _norm("%s %s" % (self.product_name, self.product_ref))
        return "gorra" in text or "cap" in text or text.startswith("kp")

    def action_add_marking(self):
        for group in self:
            position = "cap_front" if group.is_cap() else "front_left"
            technique = "embroidery" if group.is_cap() else "screen"
            color = "white" if _norm(group.color_name) in ["black", "negro", "navy", "navy blue", "marino"] else "black"
            marking = self.env["sp.personalization.marking"].create({
                "group_id": group.id,
                "name": "Marcaje cliente",
                "position": position,
                "technique": technique,
                "print_color": color,
            })
            marking.create_default_sizes()
            marking.sync_placements()
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
                    qty_float = float(qty.strip())
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
        })
        self.write({field_name: attachment.id})
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if field_name == "preview_attachment_id" or ext in ["png", "jpg", "jpeg", "webp", "svg"]:
            self.preview_image = base64.b64encode(content)
        return attachment
