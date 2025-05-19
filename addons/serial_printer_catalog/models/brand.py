from odoo import models, fields

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Brand'

    name = fields.Char(string="Nombre", required=True)
    code = fields.Char(string="Código")  # Campo requerido por la vista