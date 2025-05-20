# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variant from API'
    _rec_name = 'name'

    name = fields.Char(string='Name')
    toptex_id = fields.Char(string='TopTex ID', required=True)
    product_template_id = fields.Many2one('product.template', string='Product Template')
    attributes = fields.Char(string='Attributes')

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")

        products = response.json()

        for product in products:
            template = self.env['product.template'].search([('default_code', '=', product.get('reference'))], limit=1)
            if not template:
                continue

            for variant in product.get('variants', []):
                self.env['serial.printer.variant'].sudo().create({
                    'name': variant.get('reference', ''),
                    'toptex_id': variant.get('id', ''),
                    'product_template_id': template.id,
                    'attributes': ', '.join([
                        f"{attr.get('name')}:{attr.get('value')}"
                        for attr in variant.get('attributes', [])
                    ])
                })