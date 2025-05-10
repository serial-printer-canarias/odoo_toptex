from odoo import models, fields

class ToptexBrand(models.Model):
    _name = 'toptex.brand'
    _description = 'Marca de Toptex'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Char(string='ID Toptex', required=True)