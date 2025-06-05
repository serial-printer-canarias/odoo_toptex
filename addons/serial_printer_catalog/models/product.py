import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Paso 1: Crear producto de prueba
        try:
            self.create({
                'name': 'Producto de prueba',
                'default_code': 'TEST001',
                'type': 'consu',
                'list_price': 9.99,
                'standard_price': 5.00,
                'description_sale': 'Este es un producto de prueba.',
                'categ_id': self.env.ref('product.product_category_all').id
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {e}")
            return

        # Paso 2: Leer credenciales de parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            _logger.error("❌ Faltan credenciales o parámetros del sistema.")
            return

        # Paso 3: Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        try:
            auth_response = requests.post(
                auth_url,
                json={"username": username, "password": password},
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json"
                }
            )
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ Token no recibido.")
            _logger.info("🟢 Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al autenticar: {e}")
            return

        # Paso 4: Obtener producto desde la API
        sku = "NS300_68558_68517"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        try:
            product_response = requests.get(
                product_url,
                headers={
                    "x-api-key": api_key,
                    "x-toptex-authorization": token,
                    "Accept-Encoding": "gzip, deflate, br"
                }
            )
            if product_response.status_code != 200:
                raise UserError(f"❌ Error al obtener producto: {product_response.text}")
            data = product_response.json()
            _logger.info(f"🟢 JSON recibido:\n{data}")
        except Exception as e:
            _logger.error(f"❌ Error al obtener JSON del producto: {e}")
            return

        # Paso 5: Mapear y crear producto real
        try:
            name = data.get('translatedName', {}).get('es', data.get('designation'))
            default_code = data.get('sku', sku)
            description = data.get('description', {}).get('es') or data.get('description', {}).get('en', '')
            list_price = float(data.get('price', {}).get('salePrice', 0.0))
            standard_price = float(data.get('price', {}).get('purchasePrice', 0.0))

            product_vals = {
                'name': name or 'Producto sin nombre',
                'default_code': default_code,
                'type': 'consu',
                'list_price': list_price,
                'standard_price': standard_price,
                'description_sale': description,
                'categ_id': self.env.ref('product.product_category_all').id
            }
            self.create(product_vals)
            _logger.info("✅ Producto real creado correctamente con datos reales.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto desde JSON: {e}")