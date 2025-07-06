import logging
import requests
import time
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

        # 3. Descargar el JSON de productos (espera si es necesario)
        products_data = []
        for intento in range(20):  # hasta 10 min: 20 x 30s
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json().get("items", [])
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ Esperando a que el archivo esté listo... Intento {intento + 1}/20")
            time.sleep(30)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 10 minutos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

        # 4. Crear atributos (si no existen)
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})
        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        creados = 0
        for prod in products_data:
            brand = prod.get("brand", "")
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            composition = prod.get("composition", {}).get("es", "")
            imagenes = prod.get("images", [])
            colores = prod.get("colors", [])

            # Buscar todas las combinaciones de color/talla
            color_names = set()
            size_names = set()
            color_val_objs = {}
            size_val_objs = {}

            for color in colores:
                color_name = color.get("colors", {}).get("es", "")
                if color_name:
                    color_names.add(color_name)
            for color in colores:
                for size in color.get("sizes", []):
                    size_name = size.get("size", "")
                    if size_name:
                        size_names.add(size_name)

            # Crear valores de atributo si no existen
            for cname in color_names:
                val = self.env['product.attribute.value'].search([
                    ('name', '=', cname), ('attribute_id', '=', color_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': cname, 'attribute_id': color_attr.id})
                color_val_objs[cname] = val

            for sname in size_names:
                val = self.env['product.attribute.value'].search([
                    ('name', '=', sname), ('attribute_id', '=', size_attr.id)], limit=1)
                if not val:
                    val = self.env['product.attribute.value'].create({'name': sname, 'attribute_id': size_attr.id})
                size_val_objs[sname] = val

            # Construir attribute_lines
            attribute_lines = []
            if color_val_objs:
                attribute_lines.append({
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, [v.id for v in color_val_objs.values()])]
                })
            if size_val_objs:
                attribute_lines.append({
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, [v.id for v in size_val_objs.values()])]
                })

            # Crear producto plantilla si no existe
            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if existe:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")
                continue

            vals = {
                'name': f"{brand} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': f"{description}\nComposición: {composition}",
                'categ_id': self.env.ref("product.product_category_all").id,
                'attribute_line_ids': [(0, 0, line) for line in attribute_lines],
            }
            template = self.create(vals)
            creados += 1

            # Imagen principal: la primera disponible
            if imagenes:
                img_url = imagenes[0].get("url_image")
                if img_url:
                    try:
                        img_bin = requests.get(img_url, timeout=20).content
                        template.image_1920 = img_bin.encode('base64')
                    except Exception as e:
                        _logger.warning(f"❌ Error al descargar imagen principal: {e}")

            # Mapear precios y códigos por variante (color/talla)
            for color in colores:
                color_name = color.get("colors", {}).get("es", "")
                face_img_url = color.get("packshots", {}).get("FACE", {}).get("url_packshot", "")
                for size in color.get("sizes", []):
                    size_name = size.get("size", "")
                    sku = size.get("sku", "")
                    barcode = size.get("ean", "")
                    price_cost = size.get("prices", [{}])[0].get("price", 0.0)
                    price_sale = 0.0
                    try:
                        # "publicUnitPrice": "5,72 €" --> lo dejamos para server action de precios públicos si quieres
                        price_sale = float(size.get("prices", [{}])[0].get("price", 0.0)) * 1.30  # margen 30% ejemplo
                    except:
                        price_sale = 9.95

                    # Buscar la variante correcta
                    variant = template.product_variant_ids.filtered(
                        lambda v: 
                        color_val_objs.get(color_name) in v.product_template_attribute_value_ids.mapped('product_attribute_value_id')
                        and size_val_objs.get(size_name) in v.product_template_attribute_value_ids.mapped('product_attribute_value_id')
                    )
                    if variant:
                        v = variant[0]
                        v.default_code = sku
                        v.barcode = barcode
                        v.standard_price = price_cost
                        v.lst_price = price_sale
                        # Imágenes por variante quedan para server action, o puedes poner aquí:
                        # if face_img_url: ... descargar e insertar imagen en la variante

            _logger.info(f"✅ Creada plantilla {template.name} [{template.id}] con variantes")

        _logger.info(f"🚀 FIN: {creados} plantillas con variantes, precios y descripción creadas (TopTex).")