# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'
    _order = 'create_date desc'

    # Producto base (lo que pedía la vista)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
    )

    # Datos de personalización
    logo = fields.Binary(string='Logo', attachment=True)
    tecnica_personalizacion = fields.Selection([
        ('dtf', 'DTF'),
        ('bordado', 'Bordado'),
        ('serigrafia', 'Serigrafía'),
        ('vinilo', 'Vinilo'),
    ], string='Técnica de impresión')

    posicion_diseno = fields.Selection([
        ('pecho', 'Pecho'),
        ('espalda', 'Espalda'),
        ('manga', 'Manga'),
        ('gorra_frontal', 'Gorra - Frontal'),
    ], string='Posición del diseño')

    color_impresion = fields.Char(string='Color de impresión')
    cantidad = fields.Integer(string='Cantidad', default=1)
    observaciones = fields.Text(string='Observaciones')

    # metadatos
    create_date = fields.Datetime(string='Creado', readonly=True)