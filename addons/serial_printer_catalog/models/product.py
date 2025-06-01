import requests
from odoo import models, api
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        config = self.env['ir.config_parameter'].sudo()
        token = config.get_param('toptex_token')
        api_key = config.get_param('toptex_api_key')

        if not token or not api_key:
            raise UserError("❌ Falta token o api_key en los parámetros del sistema.")

        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "x-api-key": api_key.strip(),
            "Accept": "application/json"
        }

        url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise UserError(f"❌ Error conectando con TopTex: {str(e)}")

        if not data:
            raise UserError("⚠️ La API devolvió una respuesta vacía.")

        product_data = data[0]
        self.create({
            'name': product_data.get('label', 'Producto NS300'),
            'default_code': product_data.get('reference', 'NS300'),
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
        })