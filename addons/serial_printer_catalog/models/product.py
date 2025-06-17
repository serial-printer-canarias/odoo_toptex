import requests
import json
import base64
import logging
from odoo import models, fields, api
from PIL import Image
from io import BytesIO

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros desde Odoo
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # Obtener el token
        auth_url = f'{proxy_url}/v3/authenticate'
        auth_payload = {"username": username, "password": password}
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
            token = auth_response.json().get('token')
            if not token:
                raise UserError("❌ No se recibió un token válido.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando con TopTex: {e}")
            return

        # Hacer llamada de producto (por catalog_reference)
        catalog_reference = 'NS300'
        product_url = f'{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c'
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"🔎 URL llamada producto: {product_url}")
            _logger.info(f"🔎 Headers: {headers}")
            _logger.info(f"🔎 Respuesta cruda: {response.text}")

            if response.status_code != 200:
                raise UserError(f"❌ Error al obtener el producto: {response.status_code} - {response.text}")

            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                product_data = data[0]
            elif isinstance(data, dict):
                product_data = data
            else:
                raise UserError("❌ No se encontraron datos dentro del dict")

            _logger.info(f"📦 JSON interpretado correctamente:\n{json.dumps(product_data, indent=2)}")

            # Función de safe_get para evitar errores de 'str has no attribute get'
            def safe_get(d, path, default=None):
                for key in path:
                    if isinstance(d, dict):
                        d = d.get(key, default)
                    else:
                        return default
                return d or default

            # Mapeo seguro de datos
            name = safe_get(product_data, ["translatedName", "es"], "Producto sin nombre")
            default_code = product_data.get("catalogReference", "SIN_REF")
            marca = safe_get(product_data, ["brand", "name", "es"], "Sin Marca")
            description_sale = safe_get(product_data, ["description", "es"], "")
            list_price = product_data.get("publicUnitPrice", 0.0)
            standard_price = product_data.get("purchaseUnitPrice", 0.0)

            _logger.info(f"📝 Nombre: {name}, Marca: {marca}, Precio venta: {list_price}, Precio coste: {standard_price}")

            # Buscar categoría genérica por defecto
            categ_id = self.env['product.category'].search([('name', '=', 'All')], limit=1).id

            # Buscar o crear marca
            brand_obj = self.env['product.brand'].search([('name', '=', marca)], limit=1)
            if not brand_obj:
                brand_obj = self.env['product.brand'].create({'name': marca})
                _logger.info(f"🆕 Marca creada: {marca}")

            # Crear producto
            product_vals = {
                'name': name,
                'default_code': default_code,
                'list_price': list_price,
                'standard_price': standard_price,
                'description_sale': description_sale,
                'categ_id': categ_id,
                'product_brand_id': brand_obj.id,
                'type': 'consu',
            }

            product = self.env['product.template'].create(product_vals)
            _logger.info(f"✅ Producto creado: {name}")

        except Exception as e:
            _logger.error(f"❌ Error procesando producto: {e}")
            return