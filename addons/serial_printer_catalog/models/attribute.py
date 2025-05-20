import requests
from odoo import models, fields, api

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Product Attribute'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    values = fields.Text(string='Values')

    @api.model
    def sync_attributes_from_api(self):
        url = "https://api.toptex.io/api/attributes"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE",
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for attr in data.get("hydra:member", []):
                    self.create_or_update_attribute(attr)
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"API connection failed: {str(e)}")

    def create_or_update_attribute(self, attr_data):
        code = attr_data.get("code")
        name = attr_data.get("name")
        values = ", ".join([v.get("value") for v in attr_data.get("values", [])])

        existing = self.search([('code', '=', code)], limit=1)
        values_dict = {
            "name": name,
            "code": code,
            "values": values,
        }

        if existing:
            existing.write(values_dict)
        else:
            self.create(values_dict)