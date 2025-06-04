import json
import logging
import requests

from odoo import models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_product_from_api(self):
        _logger.info("🟦 Iniciando sincronización con la API de TopTex...")

        # Obtener credenciales desde parámetros del sistema
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not username or not password or not api_key or not proxy_url:
            _logger.error("❌ Faltan credenciales en los parámetros del sistema.")
            return

        # URL para autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "apiKey": api_key
        }

        try:
            auth_response = requests.post(auth_url, json=auth_payload)
            auth_response.raise_for_status()
            token = auth_response.json()
            access_token = token.get('accessToken')
            _logger.info(f"🟢 Token recibido: {access_token}")
        except Exception as e:
            _logger.error(f"❌ Error al autenticar con TopTex: {str(e)}")
            return

        # Crear producto de prueba
        try:
            self.env['product.template'].create({
                'name': 'Producto de Prueba',
                'default_code': 'TEST123',
                'type': 'product',
                'list_price': 9.99,
            })
            _logger.info("✅ Producto de prueba creado correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error al crear producto de prueba: {str(e)}")

        # SKU a buscar
        sku = "NS300_68558_68494"
        product_url = f"{proxy_url}/v3/products?sku={sku}&usage_right=b2b_uniquement"
        headers = {
            "toptex-authorization": access_token,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            _logger.info(f"🔵 URL solicitada: {product_url}")
            _logger.info(f"🔵 Código de estado: {response.status_code}")

            if response.status_code != 200:
                _logger.error(f"❌ Error al obtener el producto de la API: {response.text}")
                return

            product_data = response.json()
            _logger.info(f"📦 Contenido recibido: {json.dumps(product_data, indent=2)}")

            # Transformar y crear producto NS300
            if isinstance(product_data, dict):
                name = product_data.get("designation", {}).get("es", "Producto sin nombre")
                default_code = product_data.get("catalogReference", sku)
                price_str = product_data.get("colors", [{}])[0].get("sizes", [{}])[0].get("publicUnitPrice", "0")
                price = float(price_str.replace("€", "").replace(",", ".").strip()) if price_str else 0.0
                image_url = product_data.get("images", [{}])[0].get("url_image", "")

                vals = {
                    'name': name,
                    'default_code': default_code,
                    'type': 'product',
                    'list_price': price,
                }

                # Descargar y adjuntar imagen si existe
                if image_url:
                    try:
                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            vals['image_1920'] = image_response.content
                            _logger.info("🖼 Imagen descargada correctamente.")
                    except Exception as e:
                        _logger.warning(f"⚠️ No se pudo descargar la imagen: {e}")

                self.env['product.template'].create(vals)
                _logger.info("✅ Producto real NS300 creado correctamente.")
            else:
                _logger.warning("⚠️ El contenido recibido no es un diccionario válido.")

        except Exception as e:
            _logger.error(f"❌ Error general durante la sincronización: {e}")