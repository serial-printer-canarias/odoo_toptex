# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'
    _order = 'create_date desc'

    product_tmpl_id = fields.Many2one(
        'product.template', string='Producto', required=True, ondelete='cascade'
    )
    logo = fields.Binary(string='Logo')
    logo_filename = fields.Char(string='Nombre del archivo')

    tecnica_personalizacion = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('vinilo', 'Vinilo'),
    ], string='Técnica de impresión')

    posicion_diseno = fields.Selection([
        ('pecho_izquierdo', 'Pecho izquierdo'),
        ('pecho_derecho', 'Pecho derecho'),
        ('frontal', 'Frontal'),
        ('espalda', 'Espalda'),
        ('manga', 'Manga'),
    ], string='Posición')

    color_impresion = fields.Char(string='Color de impresión')
    cantidad = fields.Integer(string='Cantidad', default=1)
    observaciones = fields.Text(string='Observaciones')