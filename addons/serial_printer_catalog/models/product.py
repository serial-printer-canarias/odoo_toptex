import requests
from odoo import models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductSync(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        config = self.env['ir.config_parameter'].sudo()
        api_key = config.get_param('toptex_api_key')
        token = config.get_param('toptex_token')  # Pegado manual desde Postman

        if not api_key or not token:
            raise UserError("❌ Faltan parámetros del sistema: api_key o token")

        url = "https://api.toptex.io/v3/products?catalog_reference=ns300&usage_right=b2b_uniquement"
        headers = {
            "x-api-key": api_key,
            "Authorization": f"Bearer {token}"
        }

        try:
            res = requests.get(url, headers=headers, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            raise UserError(f"❌ Error al obtener producto NS300: {str(e)}")

        if not isinstance(data, list) or not data:
            raise UserError(f"❌ Respuesta vacía o inesperada de TopTex: {data}")

        for product in data:
            ref = product.get("reference")
            label = product.get("label")

            if not ref or not label:
                _logger.warning("⚠️ Producto sin referencia o nombre, se omite.")
                continue

            existing = self.search([('default_code', '=', ref)], limit=1)
            if existing:
                _logger.info(f"🔄 Producto {ref} ya existe, se omite.")
                continue

            self.create({
                'name': label,
                'default_code': ref,
                'type': 'product',
                'detailed_type': 'product',
            })
            _logger.info(f"✅ Producto {ref} creado correctamente.")