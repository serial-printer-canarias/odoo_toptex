import logging
import requests
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

        # 3. Descargar el JSON de productos (hasta 20 minutos si es necesario)
        import time
        for intento in range(80):  # hasta 20 minutos
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ Esperando a que el archivo esté listo... Intento {intento + 1}/80")
            time.sleep(15)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 20 minutos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

        # 4. Mapear atributos globales de color y talla
        attr_obj = self.env['product.attribute']
        color_attr = attr_obj.search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = attr_obj.create({'name': 'Color'})
        size_attr = attr_obj.search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = attr_obj.create({'name': 'Talla'})

        creados = 0
        for prod in products_data:
            brand = prod.get("brand", "TopTex")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            price = prod.get("prices", {}).get("public", 0.0)
            cost = prod.get("prices", {}).get("purchase", 0.0)
            image_url = prod.get("visuals", [{}])[0].get("url", "")
            colors = [c.get("name", {}).get("es", "") for c in prod.get("colors", []) if c.get("name", {}).get("es", "")]
            sizes = [s for s in prod.get("sizes", []) if s]
            
            # Crear valores variantes
            color_vals = []
            for color in colors:
                val = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': color, 'attribute_id': color_attr.id})
                color_vals.append(val.id)

            size_vals = []
            for size in sizes:
                val = self.env['product.attribute.value'].search([('name', '=', size), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': size, 'attribute_id': size_attr.id})
                size_vals.append(val.id)

            attribute_line_ids = []
            if color_vals:
                attribute_line_ids.append((0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, color_vals)]
                }))
            if size_vals:
                attribute_line_ids.append((0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, size_vals)]
                }))

            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': attribute_line_ids,
                'list_price': price or 0.0,
                'standard_price': cost or 0.0,
                # 'image_1920': image_binary  # Se carga luego abajo
            }
            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                creados += 1
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")

                # Descargar y asignar imagen principal
                if image_url:
                    try:
                        img_data = requests.get(image_url).content
                        template.write({'image_1920': img_data})
                        _logger.info(f"🖼️ Imagen principal añadida para {template.name}")
                    except Exception as e:
                        _logger.error(f"❌ Error al descargar imagen: {image_url} {str(e)}")
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

        _logger.info(f"🚀 FIN: {creados} plantillas creadas con variantes, precios, imagen y descripción.")