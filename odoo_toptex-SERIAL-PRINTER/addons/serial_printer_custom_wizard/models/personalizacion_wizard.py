from odoo import models, fields

class PersonalizacionWizard(models.TransientModel):
    _name = 'personalizacion.wizard'
    _description = 'Asistente de Personalización de Producto'

    logo = fields.Binary("Logo")
    
    print_technique = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna')
    ], string="Técnica de personalización", required=True)

    design_position = fields.Selection([
        ('front', 'Frontal'),
        ('back', 'Espalda')
    ], string="Posición del diseño", required=True)

    size = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande')
    ], string="Tamaño del diseño", required=True)

    color = fields.Char("Color de impresión")
    notes = fields.Text("Observaciones")