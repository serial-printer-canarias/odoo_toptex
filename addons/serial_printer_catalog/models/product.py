import requests
from odoo import models, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_ns300_from_toptex(self):
        # Parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        catalog_ref = "ns300"

        if not proxy_url:
            raise ValueError("Falta la URL del proxy en parámetros del sistema")

        # URL final de llamada
        url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}"

        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'identity',
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extraer información básica del producto
            product_data = data.get("data")
            if not product_data:
                raise ValueError("No se encontró el producto NS300 en la respuesta")

            name = product_data.get('name')
            default_code = product_data.get('reference')

            if not name or not default_code:
                raise ValueError("Faltan datos clave en la respuesta de la API")

            # Verificar si el producto ya existe
            existing = self.search([('default_code', '=', default_code)], limit=1)
            if existing:
                return  # Ya está creado

            # Crear el producto
            self.create({
                'name': name,
                'default_code': default_code,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': False,
            })

        except Exception as e:
            raise ValueError(f"Error al sincronizar producto desde TopTex: {e}")