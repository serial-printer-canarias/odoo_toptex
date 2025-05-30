import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado desde TopTex'

    name = fields.Char('Nombre del producto')
    reference = fields.Char('Referencia')
    description = fields.Text('Descripción')

    @api.model
    def sync_product_from_toptex(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_user = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        api_password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        if not proxy_url or not api_user or not api_password or not api_key:
            raise UserError("Faltan parámetros del sistema (proxy_url, username, password o api_key).")

        # Obtener token
        token_response = requests.post(
            f"{proxy_url}/v3/authenticate",
            json={"login": api_user, "password": api_password},
            headers={"x-toptex-apikey": api_key}
        )
        if token_response.status_code != 200:
            raise UserError(f"Error al obtener token: {token_response.text}")
        token = token_response.json().get('token')
        if not token:
            raise UserError("Token no recibido desde la API de TopTex.")

        # Llamada al producto NS300
        product_response = requests.get(
            f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement",
            headers={
                "x-toptex-apikey": api_key,
                "x-toptex-authorization": token,
                "Accept-Encoding": "identity"
            }
        )
        if product_response.status_code != 200:
            raise UserError(f"Error al obtener producto: {product_response.text}")

        product_data = product_response.json()
        if not product_data or not isinstance(product_data, list):
            raise UserError("No se recibió un listado de productos válido.")

        product_info = product_data[0]
        name = product_info.get('name')
        reference = product_info.get('reference')
        description = product_info.get('description', {}).get('full', '')

        if not reference:
            raise UserError("Referencia del producto no encontrada.")

        existing_product = self.env['serial.printer.product'].search([('reference', '=', reference)], limit=1)
        if existing_product:
            existing_product.write({'name': name, 'description': description})
        else:
            self.create({
                'name': name,
                'reference': reference,
                'description': description,
            })