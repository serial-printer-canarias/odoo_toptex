import requests
import json
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        _logger.info("🔄 Iniciando sincronización con la API de TopTex...")

        # Obtener parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.warning("❌ Faltan credenciales en los parámetros del sistema.")
            return

        # Generar token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload)
            auth_response.raise_for_status()
        except Exception as e:
            _logger.warning(f"❌ Error al autenticar con TopTex: {e}")
            return

        token = auth_response.json().get('token')
        if not token:
            _logger.warning("❌ No se recibió token de autenticación.")
            return
        _logger.info("✅ Token recibido correctamente.")

        # Llamada a producto por SKU
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products/sku/{sku}?usage_right=b2b_uniquement"
        headers = {'Authorization': f'Bearer {token}'}

        try:
            product_response = requests.get(product_url, headers=headers)
            product_response.raise_for_status()
            _logger.info(f"📡 Petición enviada a: {product_url}")
            _logger.info(f"📦 Código HTTP: {product_response.status_code}")
        except Exception as e:
            _logger.warning(f"❌ Error al consultar el producto: {e}")
            return

        try:
            product_data = product_response.json()
            _logger.info(f"📥 JSON recibido: {json.dumps(product_data, indent=2)[:1000]}")  # Primeros 1000 chars
        except Exception as e:
            _logger.warning(f"❌ Error al interpretar el JSON: {e}")
            return

        # Validación de contenido
        if not isinstance(product_data, dict) or not product_data:
            _logger.warning("⚠️ El JSON recibido está vacío o no es un diccionario.")
        else:
            # Crear producto desde API
            name = product_data.get("designation", {}).get("es", "Producto sin nombre")
            default_code = product_data.get("supplierReference", sku)
            description = product_data.get("description", {}).get("es", "")
            list_price = 8.60  # Valor por defecto si no viene en el JSON

            # Verificar si ya existe
            existing = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if existing:
                _logger.info(f"ℹ️ Producto {default_code} ya existe en Odoo. No se crea de nuevo.")
            else:
                try:
                    # Cargar imagen
                    image_url = product_data.get("images", [{}])[0].get("url_image")
                    image_response = requests.get(image_url) if image_url else None
                    image_data = image_response.content if image_response and image_response.ok else None

                    product_vals = {
                        'name': name,
                        'default_code': default_code,
                        'list_price': list_price,
                        'type': 'product',
                        'description_sale': description,
                    }

                    if image_data:
                        product_vals['image_1920'] = image_data

                    product = self.env['product.template'].create(product_vals)
                    _logger.info(f"✅ Producto {name} creado correctamente desde la API.")
                except Exception as e:
                    _logger.warning(f"❌ Error al crear producto desde API: {e}")

        # ✅ PRUEBA: Crear producto de test local
        try:
            prueba_name = "Producto de prueba"
            prueba_code = "TEST1234"
            ya_existe = self.env['product.template'].search([('default_code', '=', prueba_code)])
            if not ya_existe:
                prueba = self.env['product.template'].create({
                    'name': prueba_name,
                    'default_code': prueba_code,
                    'list_price': 9.99,
                    'type': 'product',
                    'description_sale': 'Este es un producto de prueba creado directamente desde product.py',
                })
                _logger.info(f"✅ Producto de prueba '{prueba_name}' creado correctamente.")
            else:
                _logger.info("ℹ️ Producto de prueba ya existe. No se creó de nuevo.")
        except Exception as e:
            _logger.warning(f"❌ Error al crear producto de prueba: {e}")