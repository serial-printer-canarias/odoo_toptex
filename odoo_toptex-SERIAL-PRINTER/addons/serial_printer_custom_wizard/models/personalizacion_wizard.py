from odoo import models, fields

class PersonalizationWizard(models.TransientModel):
    _name = 'personalization.wizard'
    _description = 'Personalization Wizard'

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
    ], string="Posición del diseño")

    size = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande')
    ], string="Tamaño del diseño")

    color = fields.Char("Color de impresión")
    notes = fields.Text("Observaciones")