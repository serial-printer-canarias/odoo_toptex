import requests
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        # Leer parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')
        token = self.env['ir.config_parameter'].sudo().get_param('toptex_token')

        # Validación
        if not proxy_url or not api_key or not token:
            raise UserError("⚠️ Faltan parámetros del sistema (proxy_url, api_key o token).")

        # Limpieza de posibles espacios en blanco
        proxy_url = proxy_url.strip()
        api_key = api_key.strip()
        token = token.strip()

        # Endpoint del producto NS300 (ajustado al proxy funcionando)
        url = f"{proxy_url}/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"

        # Headers TopTex vía proxy
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto NS300: {response.status_code} - {response.text}")

            data = response.json()
            if not data:
                raise UserError("⚠️ La respuesta del proxy está vacía o malformada.")

            producto = data[0]

            # Crear el producto en Odoo
            self.env['product.template'].create({
                'name': producto.get('name', 'Producto NS300'),
                'default_code': producto.get('catalog_reference', 'NS300'),
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })

        except Exception as e:
            raise UserError(f"❌ Error al conectar con el proxy o procesar la respuesta: {str(e)}")