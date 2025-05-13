from odoo import models, fields

class ToptexBrand(models.Model):
    _name = "toptex.brand"
    _description = "Marca externa"

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID Externo")
