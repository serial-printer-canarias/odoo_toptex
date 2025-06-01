import requests
from odoo import models, tools
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer el token manual desde el sistema
        token = self.env['ir.config_parameter'].sudo().get_param('toptex_token')
        if not token:
            raise UserError("⚠️ Falta el token de TopTex en los parámetros del sistema ('toptex_token').")

        token = token.strip()  # Quitar espacios y saltos de línea

        # URL del producto NS300
        url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"

        headers = {
            "x-toptex-authorization": token,
            "x-api-key": "",  # vacío porque no se usa en esta prueba
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto NS300: {response.status_code} - {response.text}")

            data = response.json()
            if not data:
                raise UserError("⚠️ La API devolvió una respuesta vacía.")

            # Crear producto si todo va bien
            product_data = data[0]  # el primer producto encontrado
            self.env['product.template'].create({
                'name': product_data.get('name', 'Producto NS300'),
                'default_code': product_data.get('catalog_reference', 'NS300'),
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"❌ Excepción al conectar con TopTex: {str(e)}")