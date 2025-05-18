from odoo import models, fields

class SerialPrinterBrand(models.Model):
    _name = 'serial.printer.brand'
    _description = 'Marca de productos de catálogo'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')