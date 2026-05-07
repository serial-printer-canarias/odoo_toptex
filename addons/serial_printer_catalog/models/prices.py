from odoo import models, fields, api
from odoo.exceptions import ValidationError

class SerialPrinterPrice(models.Model):
    _name = 'serial.printer.price'
    _description = 'Precio personalizado por cliente'
    _rec_name = 'product_sku'
    _sql_constraints = [
        ('sku_customer_unique', 'unique(product_sku, customer_id)', 'Ya existe un precio para este producto y cliente.')
    ]

    product_sku = fields.Char(string='SKU del producto', required=True)
    customer_id = fields.Many2one('res.partner', string='Cliente', required=True, domain=[('customer_rank', '>', 0)])
    price = fields.Float(string='Precio personalizado', required=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=lambda self: self.env.company.currency_id.id)

    # Información adicional (opcional)
    product_template_id = fields.Many2one('product.template', string='Producto relacionado', readonly=True)

    @api.constrains('price')
    def _check_price_positive(self):
        for rec in self:
            if rec.price <= 0:
                raise ValidationError("El precio debe ser mayor que cero.")

    @api.model
    def create_or_update_price(self, sku, customer_code, price):
        customer = self.env['res.partner'].search([('ref', '=', customer_code)], limit=1)
        if not customer:
            raise ValidationError(f"No se encontró el cliente con código: {customer_code}")

        existing = self.search([('product_sku', '=', sku), ('customer_id', '=', customer.id)], limit=1)

        values = {
            'product_sku': sku,
            'customer_id': customer.id,
            'price': price,
            'currency_id': self.env.company.currency_id.id,
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)