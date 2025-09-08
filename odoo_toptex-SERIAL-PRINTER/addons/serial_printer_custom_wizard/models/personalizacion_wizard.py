from odoo import models, fields, api

class ProductPersonalization(models.Model):
    _name = 'product.personalization'
    _description = 'Personalización de producto textil'

    name = fields.Char(string="Referencia", compute="_compute_name", store=True)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Línea de pedido')
    lead_id = fields.Many2one('crm.lead', string='Lead (preventa)')
    product_id = fields.Many2one('product.product', string='Producto personalizado', required=True)

    logo = fields.Binary(string='Logo subido', required=True)
    logo_filename = fields.Char(string='Nombre del archivo')
    technique = fields.Selection([
        ('serigrafia', 'Serigrafía'),
        ('bordado', 'Bordado'),
        ('dtf', 'DTF'),
        ('ninguna', 'Sin personalización')
    ], string='Técnica de personalización', required=True)

    position = fields.Selection([
        ('pecho', 'Pecho'),
        ('espalda', 'Espalda'),
        ('manga_derecha', 'Manga derecha'),
        ('manga_izquierda', 'Manga izquierda')
    ], string='Zona del diseño', required=True)

    print_color = fields.Selection([
        ('blanco', 'Blanco'),
        ('negro', 'Negro'),
        ('rojo', 'Rojo'),
        ('azul', 'Azul'),
        ('amarillo', 'Amarillo'),
        ('verde', 'Verde'),
        ('otro', 'Otro')
    ], string='Color de impresión', required=True)

    size = fields.Selection([
        ('pequeno', 'Diseño pequeño'),
        ('mediano', 'Diseño mediano'),
        ('grande', 'Diseño grande')
    ], string='Tamaño del diseño', required=True)

    notes = fields.Text(string='Observaciones')
    editable = fields.Boolean(string='Editable', default=True)

    @api.depends('sale_order_line_id', 'lead_id', 'product_id')
    def _compute_name(self):
        for rec in self:
            base = rec.product_id.display_name or 'Personalización'
            if rec.sale_order_line_id:
                rec.name = f"{base} (Pedido {rec.sale_order_line_id.order_id.name})"
            elif rec.lead_id:
                rec.name = f"{base} (Lead {rec.lead_id.name})"
            else:
                rec.name = base