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
        # Recuperar parámetros del sistema
        IrConfig = self.env['ir.config_parameter'].sudo()
        proxy_url = IrConfig.get_param('toptex_proxy_url')
        username = IrConfig.get_param('toptex_username')
        password = IrConfig.get_param('toptex_password')
        api_key = IrConfig.get_param('toptex_api_key')

        # Obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        headers_auth = {"x-api-key": api_key, "Content-Type": "application/json"}
        payload_auth = {"username": username, "password": password}
        response_auth = requests.post(auth_url, headers=headers_auth, json=payload_auth)

        if response_auth.status_code != 200:
            _logger.error(f"Error autenticación: {response_auth.status_code} {response_auth.text}")
            return

        token = response_auth.json().get("token")
        _logger.info("✅ Token recibido correctamente.")

        # Descargar producto por catalog_reference
        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_uniquement"
        headers = {"x-api-key": api_key, "x-toptex-authorization": token}

        response = requests.get(product_url, headers=headers)

        if response.status_code != 200:
            _logger.error(f"Error producto: {response.status_code} {response.text}")
            return

        try:
            full_response = response.json()
            data_list = full_response.get("data")
            if not data_list:
                _logger.error("❌ No se encontraron datos dentro del dict")
                return
            data = data_list[0]
        except Exception as e:
            _logger.error(f"Error parseando JSON: {e}")
            return

        _logger.info("✅ JSON principal recibido:")
        _logger.info(json.dumps(data, indent=2))

        # Mapping de campos principales
        name = data.get("designation", {}).get("es", "Sin nombre")
        description = data.get("description", {}).get("es", "")
        default_code = data.get("catalogReference", catalog_reference)

        # Marca
        brand_data = data.get("brand", {})
        brand_name = brand_data.get("name", {}).get("es", "Sin Marca")

        # Precio de venta
        public_price = data.get("publicUnitPrice", 0.0)
        purchase_price = data.get("purchaseUnitPrice", 0.0)
        stock = data.get("stock", 0)

        # Procesar imagen principal
        image_url = None
        images = data.get("images", [])
        if images:
            for img in images:
                if img.get("isMain"):
                    image_url = img.get("url")
                    break

        image_binary = False
        if image_url:
            try:
                img_response = requests.get(image_url)
                if img_response.status_code == 200:
                    image = Image.open(BytesIO(img_response.content))
                    buffer = BytesIO()
                    image.save(buffer, format="PNG")
                    image_binary = base64.b64encode(buffer.getvalue())
            except Exception as img_err:
                _logger.warning(f"No se pudo procesar imagen: {img_err}")

        # Crear categoría por defecto si no existe
        category = self.env['product.category'].search([('name', '=', 'All Products')], limit=1)
        if not category:
            category = self.env['product.category'].create({'name': 'All Products'})

        # Buscar marca o crear
        brand_obj = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
        if not brand_obj:
            brand_obj = self.env['product.brand'].create({'name': brand_name})

        # Crear producto principal
        product = self.create({
            'name': name,
            'default_code': default_code,
            'list_price': public_price,
            'standard_price': purchase_price,
            'type': 'product',
            'categ_id': category.id,
            'description_sale': description,
            'image_1920': image_binary,
            'quantity_on_hand': stock,
            'product_brand_id': brand_obj.id,
        })

        _logger.info(f"✅ Producto creado: {name}")
        _logger.info("✅ Sincronización inicial terminada correctamente.")