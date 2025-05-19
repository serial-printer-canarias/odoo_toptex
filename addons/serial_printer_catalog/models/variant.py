# -*- coding: utf-8 -*-
import requests
from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    toptex_variant_id = fields.Char(string='TopTex Variant ID', index=True)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_variants_from_api(self):
        """Sincroniza variantes desde la API de TopTex y crea product.product"""
        url = "https://api.toptex.io/v3/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            for variant in data.get("data", []):
                template = self.env['product.template'].sudo().search([
                    ("toptex_id", "=", variant.get("product_id"))
                ], limit=1)

                if not template:
                    continue

                vals = {
                    "product_tmpl_id": template.id,
                    "name": f"{template.name} - {variant.get('color')} / {variant.get('size')}",
                    "default_code": variant.get("sku"),
                    "toptex_variant_id": variant.get("id"),
                }

                existing = self.env['product.product'].sudo().search([
                    ('toptex_variant_id', '=', variant.get('id'))
                ], limit=1)

                if existing:
                    existing.write(vals)
                else:
                    self.env['product.product'].sudo().create(vals)

        except Exception as e:
            raise Exception(f"Error al sincronizar variantes de TopTex: {e}")