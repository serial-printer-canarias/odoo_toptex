# -*- coding: utf-8 -*-
import requests
from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        # Obtener parámetros del sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        if not proxy_url:
            raise ValueError("Falta el parámetro del sistema 'toptex_proxy_url'.")

        catalog_ref = "ns300"
        url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_uniquement"

        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'identity',
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            product_data = data.get('products') or data
            if not product_data:
                raise ValueError("No se encontró el producto NS300 en la respuesta.")

            for product in product_data:
                name = product.get("label")
                reference = product.get("catalogReference")

                if name and reference:
                    existing = self.env['product.template'].search([('default_code', '=', reference)])
                    if not existing:
                        self.env['product.template'].create({
                            'name': name,
                            'default_code': reference,
                            'type': 'product',
                        })

        except Exception as e:
            raise ValueError(f"Error al sincronizar producto TopTex: {str(e)}")