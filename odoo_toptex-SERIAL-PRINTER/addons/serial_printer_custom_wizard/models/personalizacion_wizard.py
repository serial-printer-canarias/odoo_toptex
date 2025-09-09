from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PersonalizationWizard(models.TransientModel):
    _name = 'personalization.wizard'
    _description = 'Personalización de producto textil'

    order_id = fields.Many2one('sale.order', string='Pedido')
    product_id = fields.Many2one('product.product', string='Producto')
    design_file = fields.Binary(string='Logo del cliente', attachment=True, required=True)
    design_filename = fields.Char(string='Nombre del archivo')
    
    technique = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Sin personalización')
    ], string='Técnica', required=True)

    position = fields.Selection([
        ('pecho_izquierdo', 'Pecho izquierdo'),
        ('pecho_derecho', 'Pecho derecho'),
        ('espalda', 'Espalda'),
        ('manga_derecha', 'Manga derecha'),
        ('manga_izquierda', 'Manga izquierda'),
    ], string='Posición del diseño', required=True)

    size = fields.Selection([
        ('pequeno', 'Pequeño (≤10cm)'),
        ('mediano', 'Mediano (10-20cm)'),
        ('grande', 'Grande (≥20cm)')
    ], string='Tamaño del diseño', required=True)

    print_color = fields.Selection([
        ('blanco', 'Blanco'),
        ('negro', 'Negro'),
        ('rojo', 'Rojo'),
        ('amarillo', 'Amarillo'),
        ('azul_marino', 'Azul Marino'),
        ('verde', 'Verde'),
        ('morado', 'Morado'),
        ('gris', 'Gris'),
        ('naranja', 'Naranja'),
    ], string='Color de impresión', required=True)

    notes = fields.Text(string='Observaciones')

    @api.constrains('design_file')
    def _check_design_file(self):
        for record in self:
            if not record.design_file:
                raise ValidationError("Debes subir un archivo de diseño para continuar.")

    def confirm_personalization(self):
        # Aquí puedes guardar los datos como adjunto o generar un PDF
        self.ensure_one()
        # Lógica personalizada de guardado o creación de registro
        return {
            'type': 'ir.actions.act_window_close'
        }