import logging
import requests
from odoo import models, api, fields
from odoo.exceptions import UserError
import base64
import time

_logger = logging.getLogger(__name__)

class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    name = fields.Char('Brand', required=True)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string='Brand')

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
        products_data = []
        max_wait = 60  # Hasta 30 minutos
        for intento in range(max_wait):
            file_response = requests.get(file_url, headers=headers)
            try:
                products_data = file_response.json()
                if isinstance(products_data, list) and products_data:
                    break
            except Exception:
                pass
            _logger.info(f"⏳ Esperando a que el archivo esté listo... Intento {intento + 1}/{max_wait}")
            time.sleep(30)
        else:
            raise UserError("❌ El JSON de productos no está listo tras esperar 30 minutos.")

        _logger.info(f"💾 JSON listo con {len(products_data)} productos recibidos")

        attr_obj = self.env['product.attribute']
        val_obj = self.env['product.attribute.value']
        brand_obj = self.env['product.brand']
        stock_obj = self.env['stock.quant']

        def get_or_create_attr_and_values(attr_name, values_list):
            attr = attr_obj.search([('name', '=', attr_name)], limit=1)
            if not attr:
                attr = attr_obj.create({'name': attr_name, 'create_variant': 'always'})
            value_ids = []
            for val in values_list:
                v = val_obj.search([('name', '=', val), ('attribute_id', '=', attr.id)], limit=1)
                if not v:
                    v = val_obj.create({'name': val, 'attribute_id': attr.id})
                value_ids.append(v.id)
            return attr, value_ids

        creados = 0
        for prod in products_data:
            # ----- Marca -----
            brand_name = prod.get("brand", "TopTex")
            brand_rec = brand_obj.search([('name', '=', brand_name)], limit=1)
            if not brand_rec:
                brand_rec = brand_obj.create({'name': brand_name})

            # ----- Nombre y descripción -----
            name = prod.get("designation", {}).get("es", "Producto sin nombre")
            default_code = prod.get("catalogReference", prod.get("productReference", ""))
            description = prod.get("description", {}).get("es", "")
            price = float(prod.get("publicPrice", 0.0))
            cost = float(prod.get("costPrice", 0.0))

            # --- Colores ---
            color_values = []
            if "colors" in prod and prod["colors"]:
                color_values = [c.get("name", "") for c in prod["colors"] if c.get("name", "")]
            color_attr, color_ids = (None, [])
            if color_values:
                color_attr, color_ids = get_or_create_attr_and_values("Color", color_values)

            # --- Tallas ---
            size_values = []
            if "sizes" in prod and prod["sizes"]:
                size_values = [s.get("name", "") for s in prod["sizes"] if s.get("name", "")]
            size_attr, size_ids = (None, [])
            if size_values:
                size_attr, size_ids = get_or_create_attr_and_values("Talla", size_values)

            # --- Imagen principal ---
            image_url = prod.get("image", "")
            image_base64 = False
            if image_url:
                try:
                    img_resp = requests.get(image_url)
                    if img_resp.status_code == 200:
                        image_base64 = base64.b64encode(img_resp.content)
                except Exception as e:
                    _logger.warning(f"Error descargando imagen: {image_url}")

            vals = {
                'name': f"{brand_name} {name}".strip(),
                'default_code': default_code,
                'type': 'consu',
                'is_storable': True,
                'description_sale': description,
                'categ_id': self.env.ref("product.product_category_all").id,
                'list_price': price,
                'standard_price': cost,
                'image_1920': image_base64 if image_base64 else False,
                'brand_id': brand_rec.id,
                'attribute_line_ids': [],
            }

            attribute_lines = []
            if color_attr and color_ids:
                attribute_lines.append((0, 0, {
                    'attribute_id': color_attr.id,
                    'value_ids': [(6, 0, color_ids)],
                }))
            if size_attr and size_ids:
                attribute_lines.append((0, 0, {
                    'attribute_id': size_attr.id,
                    'value_ids': [(6, 0, size_ids)],
                }))
            if attribute_lines:
                vals['attribute_line_ids'] = attribute_lines

            existe = self.env['product.template'].search([('default_code', '=', default_code)], limit=1)
            if not existe:
                template = self.create(vals)
                creados += 1
                _logger.info(f"✅ Creada plantilla {template.name} [{template.id}]")

                # ------- Imágenes por variante -------
                if color_attr and "variant_images" in prod:
                    for color in prod.get("variant_images", []):
                        color_name = color.get("color")
                        img_url = color.get("image_url")
                        if not (color_name and img_url):
                            continue
                        variant = self.env['product.product'].search([
                            ('product_tmpl_id', '=', template.id),
                            ('product_template_attribute_value_ids.name', '=', color_name)
                        ], limit=1)
                        if variant:
                            try:
                                img_resp = requests.get(img_url)
                                if img_resp.status_code == 200:
                                    variant.image_1920 = base64.b64encode(img_resp.content)
                            except Exception:
                                pass

                # ------- STOCK por variante -------
                if 'stock' in prod and prod['stock']:
                    for s in prod['stock']:
                        domain = [('product_tmpl_id', '=', template.id)]
                        if color_attr and s.get('color'):
                            domain += [('product_template_attribute_value_ids.attribute_id', '=', color_attr.id),
                                       ('product_template_attribute_value_ids.name', '=', s.get('color'))]
                        if size_attr and s.get('size'):
                            domain += [('product_template_attribute_value_ids.attribute_id', '=', size_attr.id),
                                       ('product_template_attribute_value_ids.name', '=', s.get('size'))]
                        variant = self.env['product.product'].search(domain, limit=1)
                        if variant:
                            stock_obj.sudo().create({
                                'product_id': variant.id,
                                'location_id': 1,  # Cambia si tu location_id es diferente
                                'quantity': s.get('quantity', 0)
                            })
            else:
                _logger.info(f"⏭️ Ya existe plantilla {existe.name} [{existe.id}]")

        _logger.info(f"🚀 FIN: {creados} plantillas de producto creadas con variantes, precios, imágenes y stock (TopTex).")