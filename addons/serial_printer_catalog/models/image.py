import requests
from odoo import models, api, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def sync_images_from_api(self):
        url = "https://api.toptex.io/api/products"
        headers = {
            "x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Error {response.status_code}: {response.text}")

        data = response.json()

        for item in data:
            product = self.search([('default_code', '=', item.get('sku'))], limit=1)
            if product and 'image' in item and item['image']:
                image_url = item['image']
                try:
                    image_response = requests.get(image_url)
                    if image_response.status_code == 200:
                        product.image_1920 = image_response.content
                except Exception as e:
                    # Solo logueamos, no interrumpimos todo
                    _logger.warning(f"No se pudo descargar la imagen de {image_url}: {str(e)}")