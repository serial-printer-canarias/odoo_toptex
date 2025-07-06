import logging
import requests
from odoo import models, api, fields
from odoo.exceptions import UserError
import time

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

        # 3. Descargar el JSON de productos (esperar hasta 25 min si hace falta)
        products_data = []
        for intento in range(50):  # 50 x 30s = 25min
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ Esperando a que el archivo esté listo... Intento {intento + 1}/50")
            time.sleep(30)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 25 minutos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

        # 4. Creación masiva
        for prod in products_data:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            price = prod.get("publicPrice", {}).get("EUR", 0.0)
            cost = prod.get("costPrice", {}).get("EUR", 0.0)
            categ_id = self.env.ref("product.product_category_all").id

            # Variantes: Colores y Tallas
            colores = []
            tallas = []
            variantes = prod.get("variants", [])
            for v in variantes:
                color = v.get("color", {}).get("name", {}).get("es")
                talla = v.get("size", {}).get("name", {}).get("es")
                if color and color not in colores:
                    colores.append(color)
                if talla and talla not in tallas:
                    tallas.append(talla)

            # Mapear o crear atributos
            color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
            if not color_attr:
                color_attr = self.env['product.attribute'].create({'name': 'Color'})
            talla_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
            if not talla_attr:
                talla_attr = self.env['product.attribute'].create({'name': 'Talla'})

            # Crear valores de atributo
            color_vals = []
            for color in colores:
                v = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', color_attr.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].create({'name': color, 'attribute_id': color_attr.id})
                color_vals.append(v.id)
            talla_vals = []
            for talla in tallas:
                v = self.env['product.attribute.value'].search([('name', '=', talla), ('attribute_id', '=', talla_attr.id)], limit=1)
                if not v:
                    v = self.env['product.attribute.value'].create({'name': talla, 'attribute_id': talla_attr.id})
                talla_vals.append(v.id)

            # Preparar lineas de variantes (solo si hay)
            attribute_lines = []
            if color_vals:
                attribute_lines.append((0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, color_vals)]}))
            if talla_vals:
                attribute_lines.append((0, 0, {'attribute_id': talla_attr.id, 'value_ids': [(6, 0, talla_vals)]}))

            # Imagen principal (si existe)
            image_url = prod.get("visuals", [{}])[0].get("urls", {}).get("original", "")
            main_image = False
            if image_url:
                try:
                    main_image = requests.get(image_url).content.encode("base64")
                except Exception:
                    main_image = False

            # Crear plantilla de producto
            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': categ_id,
                'lst_price': price,
                'standard_price': cost,
                'attribute_line_ids': attribute_lines,
                'image_1920': main_image,
            }
            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

        _logger.info(f"🚀 FIN: Plantillas creadas con variantes, precio, coste, imagen principal, marca, descripción.")