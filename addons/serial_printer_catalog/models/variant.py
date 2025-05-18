from odoo import models, fields

class SerialPrinterVariant(models.Model):
    _name = 'serial.printer.variant'
    _description = 'Product Variant'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    size = fields.Char(string='Size')
    color = fields.Char(string='Color')
    stock = fields.Integer(string='Stock')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')