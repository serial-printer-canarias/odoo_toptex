from odoo import models, fields, api
from odoo.exceptions import UserError


class PersonalizationWizard(models.TransientModel):
    _name = 'personalization.wizard'
    _description = 'Asistente de Personalización de Pedido'

    order_id = fields.Many2one('sale.order', string='Pedido', required=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    image_front = fields.Image(string='Vista Frontal (desde Odoo)')
    image_back = fields.Image(string='Vista Trasera (opcional)')
    
    logo = fields.Binary(string="Logo del Cliente", required=True, help="Sube tu logo en PNG con fondo transparente si es posible.")
    logo_filename = fields.Char(string="Nombre del archivo")
    
    technique = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Ninguna')
    ], string="Técnica de personalización", required=True)

    print_size = fields.Selection([
        ('pequeno', 'Pequeño'),
        ('mediano', 'Mediano'),
        ('grande', 'Grande')
    ], string="Tamaño del diseño", required=True)

    print_position = fields.Selection([
        ('pecho', 'Pecho'),
        ('espalda', 'Espalda'),
        ('manga', 'Manga'),
        ('otros', 'Otros')
    ], string="Posición del diseño", required=True)

    print_color = fields.Selection([
        ('white', 'Blanco'),
        ('black', 'Negro'),
        ('gold', 'Oro'),
        ('silver', 'Plata'),
        ('navy', 'Marino'),
        ('red', 'Rojo'),
        ('green', 'Verde'),
        ('yellow', 'Amarillo')
        # Puedes extender esta lista según la carta de colores NS300
    ], string="Color de impresión", required=True)

    notes = fields.Text(string="Observaciones para el taller")

    def action_confirm_personalization(self):
        # Validación básica
        if not self.logo:
            raise UserError("Debes subir el logo del cliente antes de continuar.")
        
        # Guardar los datos en un modelo persistente si hace falta
        self.env['personalization.record'].create({
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'logo': self.logo,
            'logo_filename': self.logo_filename,
            'technique': self.technique,
            'print_size': self.print_size,
            'print_position': self.print_position,
            'print_color': self.print_color,
            'notes': self.notes,
            'image_front': self.image_front,
            'image_back': self.image_back,
        })

        # Acciones adicionales como generar PDF, enviar por email, etc., se pueden hacer desde aquí
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '¡Personalización guardada!',
                'message': 'El pedido ha sido personalizado correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }