import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_id = fields.Integer("ID TopTex", index=True)

    @api.model
    def sync_products_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for prod in products:
                self.env['product.template'].sudo().update_or_create_product(prod)
        else:
            raise UserError(f"Error al obtener productos: {response.status_code} - {response.text}")

    @api.model
    def update_or_create_product(self, prod):
        existing = self.search([('toptex_id', '=', prod.get('id'))], limit=1)
        values = {
            'name': prod.get('name'),
            'default_code': prod.get('reference'),
            'list_price': prod.get('price', 0.0),
            'toptex_id': prod.get('id'),
            'type': 'product'
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)

    @api.model
    def sync_stock_from_api(self):
        url = "https://api.toptex.io/api/stocks"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            stocks = response.json()
            for stock in stocks:
                product = self.search([('toptex_id', '=', stock.get('product_id'))], limit=1)
                if product:
                    product.qty_available = stock.get('quantity', 0)
        else:
            raise UserError(f"Error al obtener stock: {response.status_code}")

    @api.model
    def sync_images_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            products = response.json()
            for prod in products:
                image_url = prod.get('image')
                if image_url:
                    product = self.search([('toptex_id', '=', prod.get('id'))], limit=1)
                    if product:
                        image = requests.get(image_url)
                        if image.status_code == 200:
                            product.image_1920 = image.content
        else:
            raise UserError(f"Error al obtener imágenes: {response.status_code}")

    @api.model
    def sync_prices_for_customers(self):
        # Aquí puedes aplicar reglas personalizadas de precios por cliente
        # Esto es solo un ejemplo simple
        customers = self.env['res.partner'].search([('customer_rank', '>', 0)])
        for customer in customers:
            for product in self.search([]):
                # Crear o actualizar tarifa personalizada para este cliente
                self.env['product.pricelist.item'].create({
                    'pricelist_id': customer.property_product_pricelist.id,
                    'product_tmpl_id': product.id,
                    'fixed_price': product.list_price * 0.95,  # ejemplo: 5% descuento
                })