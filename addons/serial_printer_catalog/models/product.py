# -*- coding: utf-8 -*-
import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

TOPTEX_API_URL = "https://api.toptex.io"
API_KEY = "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE"

HEADERS = {
    "x-api-key": API_KEY,
    "accept": "application/json",
}

class ProductTemplate(models.Model):
    _inherit = "product.template"

    toptex_id = fields.Char("TopTex ID", index=True)
    toptex_sku = fields.Char("TopTex SKU", index=True)

    @api.model
    def sync_products_from_api(self):
        """Sincroniza productos desde la API de TopTex"""
        try:
            url = f"{TOPTEX_API_URL}/v3/products"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            products = response.json()

            for product in products.get("data", []):
                self.env["product.template"].sudo().create({
                    "name": product.get("name"),
                    "toptex_id": product.get("id"),
                    "toptex_sku": product.get("sku"),
                    "type": "product",
                    "list_price": product.get("price", 0.0),
                    "default_code": product.get("sku"),
                })
            _logger.info("Productos importados correctamente desde TopTex")
        except Exception as e:
            _logger.error(f"Error al importar productos desde TopTex: {e}")
            raise

    @api.model
    def sync_stock_from_api(self):
        """Sincroniza stock desde la API de TopTex"""
        try:
            url = f"{TOPTEX_API_URL}/v3/stock"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            stock_data = response.json()

            for item in stock_data.get("data", []):
                template = self.env["product.template"].sudo().search([
                    ("toptex_id", "=", item.get("product_id"))
                ], limit=1)
                if template:
                    qty = item.get("quantity", 0.0)
                    template.qty_available = qty
            _logger.info("Stock actualizado correctamente desde TopTex")
        except Exception as e:
            _logger.error(f"Error al sincronizar stock desde TopTex: {e}")
            raise

    @api.model
    def sync_images_from_api(self):
        """Sincroniza imágenes desde la API de TopTex"""
        try:
            url = f"{TOPTEX_API_URL}/v3/images"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            images = response.json()

            for img in images.get("data", []):
                product = self.env["product.template"].sudo().search([
                    ("toptex_id", "=", img.get("product_id"))
                ], limit=1)
                if product and img.get("url"):
                    image_content = requests.get(img["url"]).content
                    product.image_1920 = image_content
            _logger.info("Imágenes sincronizadas correctamente desde TopTex")
        except Exception as e:
            _logger.error(f"Error al sincronizar imágenes desde TopTex: {e}")
            raise

    @api.model
    def sync_prices_from_api(self):
        """Sincroniza precios personalizados desde la API de TopTex"""
        try:
            url = f"{TOPTEX_API_URL}/v3/prices"
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            prices = response.json()

            for item in prices.get("data", []):
                product = self.env["product.template"].sudo().search([
                    ("toptex_id", "=", item.get("product_id"))
                ], limit=1)
                if product:
                    product.list_price = item.get("price", 0.0)
            _logger.info("Precios personalizados actualizados correctamente desde TopTex")
        except Exception as e:
            _logger.error(f"Error al sincronizar precios desde TopTex: {e}")
            raise