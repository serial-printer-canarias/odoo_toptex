# models/personalizacion_wizard.py

from odoo import models, fields, api

class PersonalizacionWizard(models.TransientModel):
    _name = 'product.personalizacion'
    _description = 'Asistente de Personalización'

    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de Pedido')
    product_id = fields.Many2one('product.product', string='Producto')
    tecnica = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna')
    ], string='Técnica de personalización', required=True)
    tamanio = fields.Selection([
        ('pequeno', 'Pequeño'),
        ('mediano', 'Mediano'),
        ('grande', 'Grande')
    ], string='Tamaño del diseño', required=True)
    posicion = fields.Selection([
        ('pecho', 'Pecho'),
        ('espalda', 'Espalda'),
        ('manga', 'Manga')
    ], string='Posición del diseño', required=True)
    color = fields.Char(string='Color de impresión')
    logo = fields.Binary(string='Logo')
    logo_filename = fields.Char(string='Nombre del archivo del logo')
    observaciones = fields.Text(string='Observaciones')