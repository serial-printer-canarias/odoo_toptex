
import requests
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

    def import_toptex_products(self):
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
            brand_name = product.get("brand", {}).get("label")
            desc = product.get("description", "")
            img = product.get("images", [{}])[0].get("url", "")
            color = product.get("color", {}).get("label", "")
            size = product.get("size", {}).get("label", "")
            brand = self.env["serial_printer.brand"].search([("name", "=", brand_name)], limit=1)
            self.env["serial_printer.product"].create({
                "name": name,
                "reference": ref,
                "brand_id": brand.id if brand else False,
                "description": desc,
                "image_url": img,
                "color": color,
                "size": size,
            })
            count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{count} productos importados',
                'type': 'success',
                'sticky': False,
            }
        }
