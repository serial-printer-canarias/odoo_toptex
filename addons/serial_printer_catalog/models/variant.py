import requests
from odoo import models, fields, api

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variantes del producto'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Integer(string="ID en TopTex", required=True, unique=True)
    attribute_ids = fields.Many2many('serial.printer.attribute', string="Atributos")
    product_template_id = fields.Many2one('product.template', string="Producto relacionado")

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            variants = response.json()
            for item in variants:
                self.env["serial.printer.variant"].sudo().update_or_create_variant(item)
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    @api.model
    def update_or_create_variant(self, item):
        existing = self.search([('toptex_id', '=', item.get('id'))], limit=1)
        product = self.env["product.template"].sudo().search([
            ('default_code', '=', item.get('product_id'))
        ], limit=1)

        values = {
            "name": item.get("name"),
            "toptex_id": item.get("id"),
            "product_template_id": product.id if product else False,
        }

        if existing:
            existing.write(values)
        else:
            existing = self.create(values)

        # Atributos
        attr_ids = []
        for attr_id in item.get("attribute_ids", []):
            attr = self.env["serial.printer.attribute"].sudo().search([
                ("toptex_id", "=", attr_id)
            ], limit=1)
            if attr:
                attr_ids.append(attr.id)

        if attr_ids:
            existing.attribute_ids = [(6, 0, attr_ids)]