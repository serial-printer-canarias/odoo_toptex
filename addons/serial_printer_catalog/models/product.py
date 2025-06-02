import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_products_from_api(self):
        # Recuperar credenciales desde parámetros del sistema
        ir_config = self.env['ir.config_parameter'].sudo()
        api_key = ir_config.get_param('toptex_api_key')
        username = ir_config.get_param('toptex_username')
        password = ir_config.get_param('toptex_password')
        proxy_url = ir_config.get_param('toptex_proxy_url')

        if not all([api_key, username, password, proxy_url]):
            raise UserError("Faltan parámetros del sistema para conectar con la API de TopTex.")

        # Paso 1: obtener token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_payload = {"username": username, "password": password}
        auth_headers = {"x-api-key": api_key}

        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        if auth_response.status_code != 200:
            raise UserError("Error al autenticar con la API de TopTex.")
        token = auth_response.json().get("token")

        if not token:
            raise UserError("No se recibió token de autenticación de TopTex.")

        # Paso 2: llamar al catálogo filtrado por catalog_reference = NS300
        catalog_url = f"{proxy_url}/v3/products/all?usage_right=b2b_uniquement&result_in_file=0"
        headers = {
            "x-api-key": api_key,
            "x-toptex-authorization": token
        }

        response = requests.get(catalog_url, headers=headers)
        if response.status_code != 200:
            raise UserError("No se pudo recuperar el catálogo desde la API de TopTex.")
        
        data = response.json()
        if not isinstance(data, list):
            raise UserError("Respuesta inesperada de la API (no es lista).")

        # Filtrar solo productos NS300
        ns300_variants = [prod for prod in data if prod.get('catalogReference') == 'NS300']

        if not ns300_variants:
            raise UserError("No se encontró el producto NS300 en la respuesta.")

        # Crear atributos
        color_attr = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
        if not color_attr:
            color_attr = self.env['product.attribute'].create({'name': 'Color'})

        size_attr = self.env['product.attribute'].search([('name', '=', 'Size')], limit=1)
        if not size_attr:
            size_attr = self.env['product.attribute'].create({'name': 'Size'})

        # Agrupar por combinación de color y talla
        variants = []
        for item in ns300_variants:
            attributes = item.get("attributes", {})
            color_name = attributes.get("color", {}).get("name", "Undefined")
            size_name = attributes.get("size", {}).get("name", "Undefined")
            sku = item.get("sku")

            # Crear valores si no existen
            color_val = self.env['product.attribute.value'].search([('name', '=', color_name), ('attribute_id', '=', color_attr.id)], limit=1)
            if not color_val:
                color_val = self.env['product.attribute.value'].create({
                    'name': color_name,
                    'attribute_id': color_attr.id
                })

            size_val = self.env['product.attribute.value'].search([('name', '=', size_name), ('attribute_id', '=', size_attr.id)], limit=1)
            if not size_val:
                size_val = self.env['product.attribute.value'].create({
                    'name': size_name,
                    'attribute_id': size_attr.id
                })

            variants.append((color_val, size_val, sku))

        # Crear template si no existe
        product_name = ns300_variants[0].get("name", {}).get("es", "NS300")
        existing_template = self.env['product.template'].search([('name', '=', product_name)], limit=1)

        if not existing_template:
            existing_template = self.env['product.template'].create({
                'name': product_name,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
                'attribute_line_ids': [
                    (0, 0, {'attribute_id': color_attr.id, 'value_ids': [(6, 0, [v[0].id for v in variants])] }),
                    (0, 0, {'attribute_id': size_attr.id, 'value_ids': [(6, 0, [v[1].id for v in variants])] })
                ]
            })

        # Asignar los SKU a cada combinación
        for variant in existing_template.product_variant_ids:
            color = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == color_attr)
            size = variant.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id == size_attr)

            for v_color, v_size, sku in variants:
                if v_color.name == color.name and v_size.name == size.name:
                    variant.default_code = sku
                    break