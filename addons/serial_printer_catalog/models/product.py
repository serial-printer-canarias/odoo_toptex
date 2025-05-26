import requests
from odoo import models, fields, _
from odoo.exceptions import UserError


class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto desde API TopTex'

    name = fields.Char(string="Nombre")
    toptex_id = fields.Char(string="ID TopTex")
    product_sku = fields.Char(string="SKU")
    brand = fields.Char(string="Marca")
    type = fields.Char(string="Tipo")
    list_price = fields.Float(string="Precio Venta")
    standard_price = fields.Float(string="Precio Coste")

    def get_token(self):
        token_obj = self.env['serial.printer.token'].search([], limit=1)
        if not token_obj or not token_obj.token:
            raise UserError(_("Token de API no encontrado. Asegúrate de generar uno válido."))
        return token_obj.token

    def sync_products_from_api(self):
        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgidvgiZe"
        }
        url = "https://api.toptex.io/v3/products"

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise UserError(f"Error al conectar con API de TopTex: {response.status_code} - {response.text}")

        products = response.json()
        for product in products:
            self.create_or_update_product(product)

    def create_or_update_product(self, product_data):
        existing = self.search([('toptex_id', '=', product_data.get('id'))], limit=1)

        values = {
            'name': product_data.get('name'),
            'toptex_id': product_data.get('id'),
            'product_sku': product_data.get('sku'),
            'brand': product_data.get('brand', {}).get('name'),
            'type': product_data.get('type'),
            'list_price': product_data.get('price', {}).get('price_with_tax', 0.0),
            'standard_price': product_data.get('price', {}).get('price_without_tax', 0.0),
        }

        if existing:
            existing.write(values)
        else:
            self.create(values)