from odoo import models, fields

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Variante del producto'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')