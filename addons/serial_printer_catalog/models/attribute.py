from odoo import models, fields

class SerialPrinterAttribute(models.Model):
    _name = 'serial.printer.attribute'
    _description = 'Atributos de productos Serial Printer'

    name = fields.Char(string='Nombre del atributo', required=True)
    code = fields.Char(string='Código del atributo')