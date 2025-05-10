
from odoo import models, fields

class ToptexBrand(models.Model):
    _name = 'toptex.brand'
    _description = 'Marca del proveedor externo'

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Char(string="ID Externo", required=True)
