import requests
from odoo import models, fields, api

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Product Variant'
    _rec_name = 'reference'

    reference = fields.Char(string='Reference', required=True)
    name = fields.Char(string='Name')
    color = fields.Char(string='Color')
    size = fields.Char(string='Size')
    toptex_id = fields.Char(string='TopTex ID')

    @api.model
    def sync_variants_from_api(self):
        url = "https://api.toptex.io/api/variants"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for variant in data.get("hydra:member", []):
                    self.create_or_update_variant(variant)
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"API connection failed: {str(e)}")

    def create_or_update_variant(self, variant_data):
        reference = variant_data.get("reference")
        name = variant_data.get("name", "")
        toptex_id = str(variant_data.get("id", ""))
        color = variant_data.get("color", {}).get("name", "")
        size = variant_data.get("size", {}).get("value", "")

        values = {
            "reference": reference,
            "name": name,
            "toptex_id": toptex_id,
            "color": color,
            "size": size,
        }

        existing = self.search([('reference', '=', reference)], limit=1)
        if existing:
            existing.write(values)
        else:
            self.create(values)