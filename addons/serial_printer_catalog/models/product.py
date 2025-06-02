import requests
from odoo import models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def sync_products_from_api(self):
        # Leer parámetros del sistema
        config = self.env['ir.config_parameter'].sudo()
        proxy_url = config.get_param('toptex_proxy_url')
        username = config.get_param('toptex_username')
        password = config.get_param('toptex_password')
        api_key = config.get_param('toptex_api_key')

        if not proxy_url or not username or not password or not api_key:
            raise UserError("❌ Faltan parámetros de sistema (proxy_url, username, password, api_key)")

        # Generar token
        auth_url = f"{proxy_url}/v3/authenticate"
        auth_data = {
            "username": username,
            "password": password
        }
        auth_headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json"
        }

        try:
            auth_response = requests.post(auth_url, json=auth_data, headers=auth_headers)
            if auth_response.status_code != 200:
                raise UserError(f"❌ Error autenticando: {auth_response.text}")
            token = auth_response.json().get("token")
            if not token:
                raise UserError("❌ No se recibió token de autenticación.")
        except Exception as e:
            raise UserError(f"❌ Error durante la autenticación: {str(e)}")

        # Llamada al producto NS300
        catalog_ref = "NS300"
        product_url = f"{proxy_url}/v3/products?catalog_reference={catalog_ref}&usage_right=b2b_uniquement"
        headers = {
            "x-toptex-authorization": token,
            "x-api-key": api_key,
            "Accept": "application/json"
        }

        try:
            response = requests.get(product_url, headers=headers)
            if response.status_code != 200:
                raise UserError(f"❌ Error obteniendo producto: {response.status_code} → {response.text}")
            data = response.json()
            if not data or catalog_ref not in data:
                raise UserError(f"⚠️ No se encontró el producto {catalog_ref} en la respuesta.")

            product_data = data[catalog_ref]
            variants = product_data.get("skus", [])
            if not variants:
                raise UserError("⚠️ No se encontraron variantes en el producto.")

            # Crear atributos si no existen
            attribute_model = self.env['product.attribute']
            attribute_value_model = self.env['product.attribute.value']
            attr_color = attribute_model.search([('name', '=', 'Color')], limit=1)
            if not attr_color:
                attr_color = attribute_model.create({'name': 'Color'})
            attr_size = attribute_model.search([('name', '=', 'Talla')], limit=1)
            if not attr_size:
                attr_size = attribute_model.create({'name': 'Talla'})

            # Crear template base
            template = self.env['product.template'].create({
                'name': product_data.get('name', catalog_ref),
                'sale_ok': True,
                'purchase_ok': True,
                'type': 'product',
                'default_code': catalog_ref,
                'attribute_line_ids': [(0, 0, {
                    'attribute_id': attr_color.id,
                    'value_ids': [(6, 0, [])],
                }), (0, 0, {
                    'attribute_id': attr_size.id,
                    'value_ids': [(6, 0, [])],
                })]
            })

            # Añadir variantes
            created_variants = []
            for variant in variants:
                color = variant.get("color", {}).get("label", "N/A")
                size = variant.get("size", {}).get("label", "N/A")
                sku = variant.get("sku")
                price = variant.get("price", {}).get("value", 0.0)

                if not sku or not color or not size:
                    continue

                # Crear valores si no existen
                val_color = attribute_value_model.search([('name', '=', color), ('attribute_id', '=', attr_color.id)], limit=1)
                if not val_color:
                    val_color = attribute_value_model.create({'name': color, 'attribute_id': attr_color.id})
                val_size = attribute_value_model.search([('name', '=', size), ('attribute_id', '=', attr_size.id)], limit=1)
                if not val_size:
                    val_size = attribute_value_model.create({'name': size, 'attribute_id': attr_size.id})

                # Añadir valor al template si no está
                if val_color not in template.attribute_line_ids.filtered(lambda l: l.attribute_id == attr_color).value_ids:
                    template.attribute_line_ids.filtered(lambda l: l.attribute_id == attr_color).write({
                        'value_ids': [(4, val_color.id)]
                    })
                if val_size not in template.attribute_line_ids.filtered(lambda l: l.attribute_id == attr_size).value_ids:
                    template.attribute_line_ids.filtered(lambda l: l.attribute_id == attr_size).write({
                        'value_ids': [(4, val_size.id)]
                    })

                created_variants.append({
                    'sku': sku,
                    'color': color,
                    'size': size,
                    'price': price
                })

            return {
                'status': 'ok',
                'template': template.name,
                'variants': created_variants
            }

        except Exception as e:
            raise UserError(f"❌ Excepción al procesar producto: {str(e)}")