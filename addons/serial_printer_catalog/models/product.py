import logging
import requests
import base64
from odoo import models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_product_from_api(self):
        icp = self.env['ir.config_parameter'].sudo()
        username = icp.get_param('toptex_username')
        password = icp.get_param('toptex_password')
        api_key = icp.get_param('toptex_api_key')
        proxy_url = icp.get_param('toptex_proxy_url')

        if not all([username, password, api_key, proxy_url]):
            raise UserError("❌ Faltan credenciales o parámetros del sistema.")

        # 1. Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}
        auth_payload = {"username": username, "password": password}
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError(f"❌ Error autenticando: {auth_response.status_code} - {auth_response.text}")
        token = auth_response.json().get("token")
        if not token:
            raise UserError("❌ No se recibió un token válido.")
        _logger.info("🔐 Token recibido correctamente.")

        # 2. Petición para obtener el enlace temporal de productos
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_b2c&result_in_file=1"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token,
            "Accept-Encoding": "gzip, deflate, br"
        }
        link_response = requests.get(catalog_url, headers=headers)
        if link_response.status_code != 200:
            raise UserError(f"❌ Error obteniendo enlace de catálogo: {link_response.status_code} - {link_response.text}")
        link_data = link_response.json()
        file_url = link_data.get('link')
        if not file_url:
            raise UserError("❌ No se recibió un enlace de descarga de catálogo.")
        _logger.info(f"🔗 Link temporal de catálogo: {file_url}")

        # 3. Descargar el JSON de productos (esperar si es necesario)
        import time
        for intento in range(20):  # Hasta 10 minutos
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ JSON no listo. Esperando 10 segundos más...")
            time.sleep(10)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 200 segundos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

        # 4. Recolecta todos los atributos necesarios para variantes
        attr_obj = self.env['product.attribute']
        attr_value_obj = self.env['product.attribute.value']

        # Asegúrate que existen los atributos 'Color' y 'Talla'
        attr_color = attr_obj.search([('name', '=', 'Color')], limit=1)
        if not attr_color:
            attr_color = attr_obj.create({'name': 'Color'})
        attr_size = attr_obj.search([('name', '=', 'Talla')], limit=1)
        if not attr_size:
            attr_size = attr_obj.create({'name': 'Talla'})

        # 5. Procesar productos
        creados = 0
        for prod in products_data:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            price = prod.get("price", {}).get("b2b", 0.0)
            cost = prod.get("cost", 0.0)
            image_url = prod.get("photos", [{}])[0].get("url", "")

            # === Variantes ===
            colores = [v.get('value') for v in prod.get('declination', []) if v.get('type') == 'color']
            tallas = [v.get('value') for v in prod.get('declination', []) if v.get('type') == 'size']
            color_values = []
            size_values = []
            for c in colores:
                val = attr_value_obj.search([('name', '=', c), ('attribute_id', '=', attr_color.id)], limit=1)
                if not val:
                    val = attr_value_obj.create({'name': c, 'attribute_id': attr_color.id})
                color_values.append(val.id)
            for t in tallas:
                val = attr_value_obj.search([('name', '=', t), ('attribute_id', '=', attr_size.id)], limit=1)
                if not val:
                    val = attr_value_obj.create({'name': t, 'attribute_id': attr_size.id})
                size_values.append(val.id)
            attribute_line_ids = []
            if color_values:
                attribute_line_ids.append((0, 0, {
                    'attribute_id': attr_color.id,
                    'value_ids': [(6, 0, color_values)]
                }))
            if size_values:
                attribute_line_ids.append((0, 0, {
                    'attribute_id': attr_size.id,
                    'value_ids': [(6, 0, size_values)]
                }))

            # === Imagen principal ===
            image_64 = False
            if image_url:
                try:
                    img_resp = requests.get(image_url)
                    if img_resp.status_code == 200:
                        image_64 = base64.b64encode(img_resp.content)
                except Exception as e:
                    _logger.warning(f"No se pudo descargar la imagen para {name}: {e}")

            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'list_price': price,
                'standard_price': cost,
                'attribute_line_ids': attribute_line_ids,
                'image_1920': image_64,
                'brand_id': False, # Si tienes módulo de marcas, aquí la lógica de asignación
            }
            # Marca si tienes product_brand en tu Odoo
            if 'brand_id' in self._fields:
                brand_obj = self.env['product.brand'].search([('name', '=', brand)], limit=1)
                if not brand_obj:
                    brand_obj = self.env['product.brand'].create({'name': brand})
                vals['brand_id'] = brand_obj.id

            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                creados += 1
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

        _logger.info(f"🚀 FIN: {creados} plantillas de producto creadas con variantes, precios y foto principal (TopTex).")