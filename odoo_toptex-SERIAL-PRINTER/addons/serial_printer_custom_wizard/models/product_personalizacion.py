from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'

    product_id = fields.Many2one(
        comodel_name='product.template',
        string='Producto',
        required=True
    )

    tecnica_personalizacion = fields.Selection(
        selection=[
            ('serigrafia', 'Serigrafía'),
            ('bordado', 'Bordado'),
            ('dtf', 'DTF'),
            ('ninguna', 'Ninguna')
        ],
        string='Técnica de personalización',
        required=True
    )

    posicion_diseno = fields.Selection(
        selection=[
            ('pecho', 'Pecho'),
            ('espalda', 'Espalda')
        ],
        string='Posición del diseño',
        required=True
    )

    tamanio_diseno = fields.Selection(
        selection=[
            ('pequeno', 'Pequeño'),
            ('mediano', 'Mediano'),
            ('grande', 'Grande')
        ],
        string='Tamaño del diseño',
        required=True
    )

    color_impresion = fields.Char(
        string='Color de impresión'
    )

    archivo_logo = fields.Binary(
        string='Archivo del logo'
    )

    archivo_logo_nombre = fields.Char(
        string='Nombre del archivo'
    )

    observaciones = fields.Text(
        string='Observaciones'
    )