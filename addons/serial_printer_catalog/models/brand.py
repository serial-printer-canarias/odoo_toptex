from odoo import models, fields

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Brand from TopTex'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)