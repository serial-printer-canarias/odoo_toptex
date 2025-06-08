import json
import logging
import base64
import requests

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

def get_image_from_url(image_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers)
        if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
            return base64.b64encode(response.content)
    except Exception as e:
        _logger.error(f"Error descargando imagen desde {image_url}: {e}")
    return False

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        # Crear producto de prueba
        self.env['product.template'].create({
            'name': 'Producto de prueba',
            'default_code': 'PRUEBA001',
            'type': 'consu',
            'list_price': 9.99,
            'standard_price': 5.00,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        _logger.info("✅ Producto de prueba creado correctamente.")

        # Leer parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        api_key = ir_config.get_param('toptex_api_key')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
        }
        auth_data = {
            "login": username,
            "password": password
        }
        auth_response = requests.post(auth_url, json=auth_data, headers=headers)
        token = auth_response.json().get("token")

        if not token:
            _logger.error("❌ No se pudo obtener el token de autenticación.")
            return

        _logger.info("✅ Token obtenido correctamente.")

        # Descargar producto real desde TopTex
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products/{sku}?usage_right=b2b_uniquement"
        product_headers = {
            "toptex-authorization": token,
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        response = requests.get(product_url, headers=product_headers)

        if response.status_code != 200:
            _logger.error(f"❌ Error al obtener el producto: {response.status_code}")
            return

        data = response.json()
        _logger.info(f"📦 JSON recibido: {json.dumps(data, indent=2)}")

        # Mapeo de datos
        product_data = {
            'name': data.get('translatedName', {}).get('es', data.get('designation')),
            'default_code': data.get('reference'),
            'list_price': data.get('price', {}).get('salePrice', 0.0),
            'standard_price': data.get('price', {}).get('purchasePrice', 0.0),
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'description_sale': data.get('description', ''),
        }

        # Marca (brand)
        brand = data.get('brand', {}).get('name')
        if brand:
            brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
            if not brand_obj:
                brand_obj = self.env['product.brand'].create({'name': brand})
            product_data['product_brand_id'] = brand_obj.id

        # Imagen principal
        image_url = data.get('images', [{}])[0].get('url')
        if image_url:
            image = get_image_from_url(image_url)
            if image:
                product_data['image_1920'] = image
            else:
                _logger.warning(f"⚠️ No se pudo cargar la imagen desde: {image_url}")

        # Crear producto real
        self.env['product.template'].create(product_data)
        _logger.info("✅ Producto real NS300 creado correctamente.")