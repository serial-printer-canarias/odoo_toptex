from odoo import models, fields

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'

    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de pedido')
    tecnica = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna'),
    ], string='Técnica', required=True)
    posicion = fields.Selection([
        ('pecho_izquierdo', 'Pecho izquierdo'),
        ('pecho_derecho', 'Pecho derecho'),
        ('espalda', 'Espalda'),
        ('manga_derecha', 'Manga derecha'),
        ('manga_izquierda', 'Manga izquierda'),
    ], string='Posición del diseño', required=True)
    color_impresion = fields.Char(string='Color de impresión')
    tamano_diseno = fields.Selection([
        ('pequeno', 'Pequeño'),
        ('mediano', 'Mediano'),
        ('grande', 'Grande'),
    ], string='Tamaño del diseño', required=True)
    logo = fields.Binary(string='Logo')
    logo_filename = fields.Char(string='Nombre del archivo')
    observaciones = fields.Text(string='Observaciones')
    editable = fields.Boolean(default=True)