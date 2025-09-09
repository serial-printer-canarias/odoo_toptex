# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'

    product_id = fields.Many2one(
        'product.template', string='Producto', required=True)
    tecnica_personalizacion = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna'),
    ], string='Técnica')
    posicion_disenyo = fields.Selection([
        ('front', 'Frontal'),
        ('back', 'Espalda'),
    ], string='Posición')
    tamano_disenyo = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande'),
    ], string='Tamaño')
    color_impresion = fields.Char(string='Color de impresión')
    notas = fields.Text(string='Observaciones')