import requests
import json
import base64
from io import BytesIO
from PIL import Image
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Leer parámetros de sistema
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex_proxy_url')
        username = self.env['ir.config_parameter'].sudo().get_param('toptex_username')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex_password')
        api_key = self.env['ir.config_parameter'].sudo().get_param('toptex_api_key')

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        auth_response = requests.post(auth_url, headers=auth_headers, json=auth_payload)
        token = auth_response.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        # Descargar producto por catalog_reference NS300
        product_url = f"{proxy_url}/v3/products?catalog_reference=NS300&usage_right=b2b_b2c"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            _logger.error(f"❌ Error en llamada a catálogo: {response.text}")
            return

        try:
            full_response = response.json()
        except Exception as e:
            _logger.error(f"❌ Error decodificando JSON: {e}")
            return

        # Seguridad: si el json es un string volvemos a convertirlo
        if isinstance(full_response, str):
            full_response = json.loads(full_response)

        # Determinar si es list o dict
        if isinstance(full_response, list):
            if not full_response:
                _logger.error("❌ No se encontraron productos en la lista.")
                return
            data = full_response[0]
        elif isinstance(full_response, dict):
            data = full_response
        else:
            _logger.error("❌ Formato de respuesta desconocido.")
            return

        _logger.info("✅ JSON principal recibido:")
        _logger.info(json.dumps(data, indent=2))

        # Extraer datos básicos
        name = data.get("designation", {}).get("es", "Producto sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", "NS300")

        brand_data = data.get("brand")
        if isinstance(brand_data, dict):
            brand = brand_data.get("name", {}).get("es", "Sin Marca")
        else:
            brand = "Sin Marca"

        brand_category = self.env['product.category'].search([('name', '=', brand)], limit=1)
        if not brand_category:
            brand_category = self.env['product.category'].create({'name': brand})

        # Imagen principal (por ahora desactivada para ir estables)
        image_bin = False

        # Crear plantilla
        template_vals = {
            'name': name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'categ_id': brand_category.id,
            'image_1920': image_bin or False,
            'standard_price': 0.0,
            'list_price': 0.0,
        }

        product_template = self.create(template_vals)
        _logger.info(f"✅ Producto creado: {product_template.name}")

        # Crear atributos (por ahora no activamos variantes hasta confirmar parsing estable)
        _logger.info("✅ Sincronización inicial terminada correctamente.")