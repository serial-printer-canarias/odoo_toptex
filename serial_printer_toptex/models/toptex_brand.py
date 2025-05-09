import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class ToptexBrand(models.Model):
    _name = 'toptex.brand'
    _description = 'Marca de Toptex'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Char(string='ID en Toptex', required=True, index=True)

    def import_brands(self):
        _logger.info("Botón de importar marcas presionado.")
        # Aquí luego se conectará con la API real