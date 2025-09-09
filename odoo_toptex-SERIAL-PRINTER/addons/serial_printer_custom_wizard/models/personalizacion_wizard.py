from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PersonalizationWizard(models.TransientModel):
    _name = 'personalization.wizard'
    _description = 'Personalization Wizard'

    product_template_id = fields.Many2one('product.template', string="Product", required=True)
    logo = fields.Binary("Logo File", required=True)
    logo_filename = fields.Char("Logo Filename")
    technique = fields.Selection([
        ('serigraphy', 'Serigrafía'),
        ('embroidery', 'Bordado'),
        ('dtf', 'DTF'),
        ('none', 'Ninguna')
    ], string="Técnica", required=True)
    position = fields.Selection([
        ('front', 'Pecho'),
        ('back', 'Espalda'),
        ('sleeve', 'Manga')
    ], string="Posición", required=True)
    size = fields.Selection([
        ('small', 'Pequeño'),
        ('medium', 'Mediano'),
        ('large', 'Grande')
    ], string="Tamaño", required=True)
    color = fields.Selection([
        ('white', 'Blanco'),
        ('black', 'Negro'),
        ('red', 'Rojo'),
        ('blue', 'Azul'),
        ('yellow', 'Amarillo')
    ], string="Color de impresión", required=True)
    notes = fields.Text("Observaciones")

    def generate_personalization_pdf(self):
        self.ensure_one()
        if not self.logo:
            raise ValidationError("Debe subir un logo.")

        # Generación de PDF en adjuntos (pendiente implementación real)
        pdf_content = b"%PDF-1.4\n%..."  # Aquí deberías generar el contenido real del PDF
        attachment = self.env['ir.attachment'].create({
            'name': f"personalizacion_{self.product_template_id.name}.pdf",
            'type': 'binary',
            'datas': pdf_content.encode('base64'),
            'res_model': 'personalization.wizard',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        # Enlace a cliente o pedido en producción (pendiente implementación real)

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }