from odoo import models, fields

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributo de producto'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')