import logging
from odoo import models, fields

class ToptexBrand(models.Model):
    _name = 'toptex.brand'
    _description = 'Marca de Toptex'

    name = fields.Char(string='Nombre', required=True)
    toptex_id = fields.Char(string='ID en Toptex', required=True, index=True)
        def import_brands(self):
        # Aquí irá luego la lógica para conectarse a la API de Toptex
        _logger = logging.getLogger(__name__)
        _logger.info("Botón de importar marcas presionado.")