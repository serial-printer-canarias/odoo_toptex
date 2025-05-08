from odoo import models, fields

class ToptexProduct(models.Model):
    _name = 'toptex.product'
    _description = 'Producto Toptex'

    name = fields.Char(string="Nombre del producto")
    reference = fields.Char(string="Referencia")