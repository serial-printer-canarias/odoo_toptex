import logging
from odoo import models, fields
from .toptex_api import ToptexAPIMixin

_logger = logging.getLogger(__name__)

class ToptexBrand(models.Model, ToptexAPIMixin):
    _name = 'toptex.brand'
    _description = 'Marca de Toptex'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Char(string='ID en Toptex', required=True, index=True)

    def import_brands(self):
        _logger.info("Botón de importar marcas presionado desde formulario.")
        self.import_toptex_brands()