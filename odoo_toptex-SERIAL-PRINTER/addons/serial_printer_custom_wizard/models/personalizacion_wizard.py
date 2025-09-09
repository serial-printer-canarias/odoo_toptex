from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'

    product_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
    )

    tecnica_personalizacion = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna'),
    ], string='Técnica de personalización', required=True)

    posicion_diseno = fields.Selection([
        ('pecho', 'Pecho'),
        ('espalda', 'Espalda'),
        ('manga_izquierda', 'Manga Izquierda'),
        ('manga_derecha', 'Manga Derecha'),
    ], string='Posición del diseño', required=True)

    color_impresion = fields.Char(string='Color de impresión')
    tamano_diseno = fields.Selection([
        ('pequeno', 'Pequeño'),
        ('mediano', 'Mediano'),
        ('grande', 'Grande'),
    ], string='Tamaño del diseño')

    observaciones = fields.Text(string='Observaciones')

    logo = fields.Binary(string='Logo')
    logo_filename = fields.Char(string="Nombre del archivo")