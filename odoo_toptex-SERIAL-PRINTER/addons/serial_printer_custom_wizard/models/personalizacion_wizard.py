from odoo import models, fields, api

class ProductPersonalizacion(models.Model):
    _name = 'product.personalizacion'
    _description = 'Personalización de producto'
    _order = 'id desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Producto', required=True, index=True, ondelete='cascade'
    )

    logo = fields.Binary('Logo')
    tecnica_personalizacion = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna'),
    ], string='Técnica de personalización', default='ninguna')

    posicion_diseno = fields.Selection([
        ('front', 'Frontal'),
        ('back', 'Espalda'),
    ], string='Posición del diseño')

    tamano_diseno = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande'),
    ], string='Tamaño del diseño')

    color_impresion = fields.Char('Color de impresión')
    observaciones = fields.Text('Observaciones')

    @api.depends('product_tmpl_id')
    def _compute_name(self):
        for rec in self:
            rec.name = (rec.product_tmpl_id.display_name or 'Producto') + ' - Personalización'