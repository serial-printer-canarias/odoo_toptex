import requests
from odoo import models, api, fields
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductSync(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        config = self.env['ir.config_parameter'].sudo()
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        api_key = config.get_param('toptex_api_key')
        proxy_url = config.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            raise UserError("❌ Faltan parámetros en el sistema (username, password, api_key o proxy_url)")

        # Paso 1: Obtener token desde el proxy
        try:
            auth_url = f"{proxy_url}/authenticate"
            response = requests.post(
                auth_url,
                json={"username": username, "password": password},
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise UserError("❌ No se recibió token de autenticación.")
        except Exception as e:
            raise UserError(f"❌ Error autenticando con TopTex vía proxy: {str(e)}")

        # Paso 2: Obtener producto NS300 desde el proxy
        try:
            headers = {
                "x-api-key": api_key,
                "Authorization": f"Bearer {token}"
            }
            product_url = f"{proxy_url}/products?catalog_reference=ns300&usage_right=b2b_uniquement"
            res = requests.get(product_url, headers=headers, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            raise UserError(f"❌ Error obteniendo producto NS300 vía proxy: {str(e)}")

        if not isinstance(data, list) or not data:
            raise UserError(f"❌ Respuesta inesperada de TopTex: {data}")

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