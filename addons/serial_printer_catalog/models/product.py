import requests
import base64
import json
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def toptex_api_token(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex.proxy_url')
        login = self.env['ir.config_parameter'].sudo().get_param('toptex.api_login')
        password = self.env['ir.config_parameter'].sudo().get_param('toptex.api_password')

        url = f"{proxy_url}/v3/token"
        payload = {
            "login": login,
            "password": password
        }
        headers = {'Content-Type': 'application/json'}

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception(f"Error autenticación TopTex: {response.text}")

    @api.model
    def sync_product_from_api(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex.proxy_url')
        token = self.toptex_api_token()
        headers = {"Authorization": f"Bearer {token}"}
        page = 0

        while True:
            paginated_url = f"{proxy_url}/v3/products/all?page={page}&limit=50"
            response = requests.get(paginated_url, headers=headers)
            if response.status_code != 200:
                break

            products = response.json()
            if not products:
                break

            for data in products:
                reference = data.get("reference")
                name = data.get("name", "")
                description = data.get("description", "")
                brand_name = data.get("brand", {}).get("name", "Marca desconocida")
                image_url = data.get("images", {}).get("front")
                price = data.get("price", {}).get("public")
                cost = data.get("price", {}).get("cost")

                brand = self.env['product.brand'].search([('name', '=', brand_name)], limit=1)
                if not brand:
                    brand = self.env['product.brand'].create({'name': brand_name})

                existing = self.env['product.template'].search([('default_code', '=', reference)], limit=1)
                if existing:
                    continue

                template = self.env['product.template'].create({
                    'name': name,
                    'default_code': reference,
                    'type': 'consu',
                    'is_storable': True,
                    'description': description,
                    'list_price': price or 0.0,
                    'standard_price': cost or 0.0,
                    'brand_id': brand.id,
                })

                # Imagen principal
                if image_url:
                    img_response = requests.get(image_url)
                    if img_response.status_code == 200:
                        template.image_1920 = base64.b64encode(img_response.content)

                # Variantes
                variants = data.get("variants", [])
                for variant in variants:
                    sku = variant.get("sku")
                    attributes = []
                    color = variant.get("color", {}).get("name")
                    size = variant.get("size", {}).get("name")

                    if color:
                        attr_color = self.env['product.attribute'].search([('name', '=', 'Color')], limit=1)
                        if not attr_color:
                            attr_color = self.env['product.attribute'].create({'name': 'Color'})
                        val_color = self.env['product.attribute.value'].search([('name', '=', color), ('attribute_id', '=', attr_color.id)], limit=1)
                        if not val_color:
                            val_color = self.env['product.attribute.value'].create({'name': color, 'attribute_id': attr_color.id})
                        attributes.append((0, 0, {'attribute_id': attr_color.id, 'value_id': val_color.id}))

                    if size:
                        attr_size = self.env['product.attribute'].search([('name', '=', 'Talla')], limit=1)
                        if not attr_size:
                            attr_size = self.env['product.attribute'].create({'name': 'Talla'})
                        val_size = self.env['product.attribute.value'].search([('name', '=', size), ('attribute_id', '=', attr_size.id)], limit=1)
                        if not val_size:
                            val_size = self.env['product.attribute.value'].create({'name': size, 'attribute_id': attr_size.id})
                        attributes.append((0, 0, {'attribute_id': attr_size.id, 'value_id': val_size.id}))

                    if attributes:
                        template.write({'attribute_line_ids': [(0, 0, {'attribute_id': a[2]['attribute_id'], 'value_ids': [(6, 0, [a[2]['value_id']])]}) for a in attributes]})

            page += 1


    # ⏬ Server Action 1: Stock por SKU
    @api.model
    def sync_stock_from_api(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex.proxy_url')
        token = self.toptex_api_token()
        headers = {"Authorization": f"Bearer {token}"}
        stock_url = f"{proxy_url}/v3/products/stock"

        response = requests.get(stock_url, headers=headers)
        if response.status_code != 200:
            return

        stock_data = response.json()
        for item in stock_data:
            sku = item.get("sku")
            qty = item.get("stock", 0)

            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if product:
                product.qty_available = qty


    # 🖼️ Server Action 2: Imágenes por variante (SKU)
    @api.model
    def sync_variant_images_from_api(self):
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('toptex.proxy_url')
        token = self.toptex_api_token()
        headers = {"Authorization": f"Bearer {token}"}
        img_url = f"{proxy_url}/v3/products/images"

        response = requests.get(img_url, headers=headers)
        if response.status_code != 200:
            return

        images = response.json()
        for item in images:
            sku = item.get("sku")
            url = item.get("front")

            product = self.env['product.product'].search([('default_code', '=', sku)], limit=1)
            if product and url:
                img_response = requests.get(url)
                if img_response.status_code == 200:
                    product.image_1920 = base64.b64encode(img_response.content)