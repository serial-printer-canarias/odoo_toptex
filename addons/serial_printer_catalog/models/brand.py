from odoo import models, fields

class SerialPrinterBrand(models.Model):
    _name = "serial.printer.brand"
    _description = "Marca del proveedor TopTex"

    name = fields.Char("Nombre", required=True)
    code = fields.Char("Código")