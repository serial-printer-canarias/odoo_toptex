# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from io import BytesIO
from PIL import Image
from odoo import models, api, exceptions

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
            raise exceptions.UserError("❌ Faltan parámetros de configuración.")

        # Autenticación
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key, "Content-Type": "application/json"}

        try:
            auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
            auth_response.raise_for_status()
            token = auth_response.json().get("token")
            if not token:
                raise exceptions.UserError("❌ No se recibió token.")
            _logger.info("✅ Token recibido correctamente.")
        except Exception as e:
            _logger.error(f"❌ Error autenticando: {e}")
            return

        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        catalog_reference = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_reference}&usage_right=b2b_b2c"

        try:
            response = requests.get(product_url, headers=headers)
            response.raise_for_status()
            data_list = response.json()
            data = data_list[0] if isinstance(data_list, list) and data_list else {}
            _logger.info(json.dumps(data, indent=2))
        except Exception as e:
            _logger.error(f"❌ Error obteniendo producto: {e}")
            return

        # Marca y datos base
        brand = data.get("brand", {}).get("name", {}).get("es", "") or "Sin Marca"
        designation = data.get("designation", {}).get("es", "Sin Nombre")
        full_name = f"{brand} {designation}".strip()
        description = data.get("description", {}).get("es", "")
        default_code = data.get("productReference", "NS300")
        list_price = float(data.get("publicUnitPrice", 0) or 0)

        # Precio coste del primer size
        standard_price = 0.0
        for color in data.get("colors", []):
            for size in color.get("sizes", []):
                price_str = size.get("wholesaleUnitPrice", "0").replace(",", ".")
                try:
                    standard_price = float(price_str)
                    break
                except:
                    continue
            if standard_price:
                break

        # Imagen principal
        image_data = None
        try:
            images = data.get("images", [])
            if images:
                img_url = images[0].get("url_image", "")
                img_data = self.download_and_resize_image(img_url)
                if img_data:
                    image_data = img_data
                    _logger.info(f"✅ Imagen principal asignada: {img_url}")
        except Exception as e:
            _logger.warning(f"⚠️ Imagen principal no asignada: {e}")

        # Creamos atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Talla'})

        color_values = []
        size_values = []

        for color in data.get("colors", []):
            color_name = color.get("color", {}).get("es", "Color desconocido")
            color_val = self.env['product.attribute.value'].search([
                ('name', '=', color_name), ('attribute_id', '=', color_attr.id)
            ], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({'name': color_name, 'attribute_id': color_attr.id})
            color_values.append(color_val)

            for size in color.get("sizes", []):
                size_name = size.get("size", "Talla desconocida")
                size_val = self.env['product.attribute.value'].search([
                    ('name', '=', size_name), ('attribute_id', '=', size_attr.id)
                ], limit=1)
                if not size_val:
                    size_val = self.env['product.attribute.value'].create({'name': size_name, 'attribute_id': size_attr.id})
                size_values.append(size_val)

        # Crear plantilla
        template_vals = {
            'name': full_name,
            'default_code': default_code,
            'type': 'consu',
            'description_sale': description,
            'list_price': list_price,
            'standard_price': standard_price,
            'categ_id': self.env.ref('product.product_category_all').id,
        }
        if image_data:
            template_vals['image_1920'] = image_data

        product_template = self.create(template_vals)

        # Asignar variantes
        product_template.write({
            'attribute_line_ids': [
                (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v.id for v in color_values])]}),
                (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v.id for v in size_values])]}),
            ]
        })

        product_template._create_variant_ids()

        # Asignar imágenes de variantes
        for variant in product_template.product_variant_ids:
            color_val = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.id == color_attr.id).name
            color_data = next((c for c in data.get("colors", []) if c.get("color", {}).get("es", "") == color_val), None)
            if color_data:
                variant_img_url = color_data.get("url_image", "")
                img_data = self.download_and_resize_image(variant_img_url)
                if img_data:
                    variant.image_variant_1920 = img_data
                    _logger.info(f"✅ Imagen asignada a variante {variant.display_name}")

        # Asignar stock
        inventory_url = f"{proxy_url}/v3/products/inventory/{catalog_reference}"
        try:
            stock_resp = requests.get(inventory_url, headers=headers)
            stock_resp.raise_for_status()
            stock_data = stock_resp.json()
            for variant in product_template.product_variant_ids:
                sku = variant.default_code
                for inv in stock_data.get("inventoryList", []):
                    if inv.get("sku") == sku:
                        qty = inv.get("availableQuantity", 0)
                        self.env['stock.quant'].create({
                            'product_id': variant.id,
                            'location_id': 1,
                            'quantity': qty
                        })
                        _logger.info(f"✅ Stock asignado a {sku}: {qty}")
                        break
        except Exception as e:
            _logger.warning(f"⚠️ Error asignando stock: {e}")

    def download_and_resize_image(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                img = Image.open(BytesIO(response.content))
                img = img.convert('RGB')
                output = BytesIO()
                img.save(output, format='PNG')
                return base64.b64encode(output.getvalue())
        except Exception as e:
            _logger.warning(f"⚠️ Error descargando imagen: {e}")
        return None