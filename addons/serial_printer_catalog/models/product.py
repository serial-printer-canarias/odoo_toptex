import requests
import base64
from odoo import models, fields

class SerialPrinterProduct(models.Model):
    _name = 'serial_printer.product'
    _description = 'Producto externo'

    name = fields.Char("Nombre", required=True)
    reference = fields.Char("Referencia")
    brand_id = fields.Many2one("serial_printer.brand", string="Marca")
    description = fields.Text("Descripción")
    image_url = fields.Char("URL Imagen")
    color = fields.Char("Color")
    size = fields.Char("Talla")
    stock = fields.Integer("Stock disponible")

    def import_products_from_api(self):
        url = "https://api.toptex.io/v3/products/all"
        headers = {
            "accept": "application/json",
            "x-api-key": "qh7SERVyz43xDDNaRONs0aLxGntfFSOX4b0vgiZe"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error en productos: {response.status_code} - {response.text}")

        data = response.json()
        count = 0
        for product in data:
            name = product.get("name")
            ref = product.get("reference")
            brand_label = product.get("brand", {}).get("label", "")
            desc = product.get("description", "")
            img = product.get("images", [{}])[0].get("url", "")
            color = product.get("color", {}).get("label", "")
            size = product.get("size", {}).get("label", "")

            # Buscar la marca asociada en base a su label.
            brand = self.env["serial_printer.brand"].search([("name", "=", brand_label)], limit=1)

            self.create({
                "name": name,
                "reference": ref,
                "brand_id": brand.id if brand else False,
                "description": desc,
                "image_url": img,
                "color": color,
                "size": size,
                "stock": 0,
            })
            count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{count} productos importados.',
                'type': 'success',
                'sticky': False,
            }
        }

    def sync_stock_from_api(self):
        url = "https://api.toptex.io/v3/products/stock"
        headers = {
            "accept": "application/json",
            "x-api-key": "qh7SERVyz43xDDNaRONs0aLxGntfFSOX4b0vgiZe"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception("Error al obtener stock")

        data = response.json()
        updated = 0
        for item in data:
            ref = item.get("reference")
            quantity = item.get("quantity")
            product = self.search([('reference', '=', ref)], limit=1)
            if product:
                product.sudo().write({'stock': quantity})
                updated += 1

        return True

    def sync_products_to_product_template(self):
        """
        Sincroniza los productos importados de TopTex con los registros de product.template en Odoo,
        de modo que queden disponibles para ventas, presupuestos y eCommerce.
        Se utiliza la referencia (default_code) para identificar el producto.
        """
        ProductTemplate = self.env['product.template']
        synced = 0
        for rec in self.search([]):
            tmpl = ProductTemplate.search([('default_code', '=', rec.reference)], limit=1)

            # Intentamos descargar la imagen desde la URL y la convertimos a base64.
            image_data = False
            if rec.image_url:
                try:
                    img_response = requests.get(rec.image_url)
                    if img_response.status_code == 200:
                        image_data = base64.b64encode(img_response.content).decode('utf-8')
                except Exception as e:
                    image_data = False

            vals = {
                'name': rec.name,
                'default_code': rec.reference,
                'sale_ok': True,
                'purchase_ok': True,
                'list_price': 100.0,  # Precio por defecto, que luego podrás modificar o aplicar tarifas.
                'description_sale': rec.description,
                'image_1920': image_data or False,
            }
            if tmpl:
                tmpl.write(vals)
            else:
                ProductTemplate.create(vals)
            synced += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{synced} productos sincronizados a product.template.',
                'type': 'success',
                'sticky': False,
            }
        }