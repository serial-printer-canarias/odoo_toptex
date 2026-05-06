# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestSerialPrinterPersonalizationLogic(TransactionCase):

    def test_required_placements_front_back_neck(self):
        group = self.env["sp.personalization.group"].create({
            "personalization_id": self.env["sp.personalization.order"].create({
                "partner_id": self.env.ref("base.res_partner_1").id,
            }).id,
            "product_name": "NS300 Camiseta",
            "color_name": "Black",
            "qty_total": 10,
            "size_summary": "S: 4 · M: 6",
        })
        marking = self.env["sp.personalization.marking"].create({
            "group_id": group.id,
            "position": "front_back_neck",
        })
        self.assertEqual(set(marking.placement_ids.mapped("placement_key")), {"front_left", "back", "neck"})

    def test_position_change_syncs_placements(self):
        order = self.env["sp.personalization.order"].create({"partner_id": self.env.ref("base.res_partner_1").id})
        group = self.env["sp.personalization.group"].create({
            "personalization_id": order.id,
            "product_name": "NS300 Camiseta",
            "color_name": "Black",
            "qty_total": 10,
            "size_summary": "S: 4 · M: 6",
        })
        marking = self.env["sp.personalization.marking"].create({"group_id": group.id, "position": "front_left"})
        self.assertEqual(marking.placement_ids.mapped("placement_key"), ["front_left"])
        marking.position = "front_back"
        self.assertEqual(set(marking.placement_ids.mapped("placement_key")), {"front_left", "back"})
