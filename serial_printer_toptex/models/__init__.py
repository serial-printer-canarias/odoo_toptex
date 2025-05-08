from . import toptex_brand
from odoo import models, fields

class ToptexBrand(models.Model):
    _name = 'toptex.brand'
    _description = 'Toptex Brand'

    name = fields.Char(string="Brand Name", required=True)
