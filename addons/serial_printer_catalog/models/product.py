import requests
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    toptex_product_id = fields.Char("TopTex ID", readonly=True)

    @api.model
    def sync_products_from_api(self):
        proxy_url = "https://toptex-proxy.onrender.com/proxy"
        toptex_url = "https://api.toptex.io/v3/products?usage_right=b2b_uniquement&result_in_file=1"
        headers = {
            "Accept-Encoding": "identity",  # evita error gzip
            "Accept": "application/json",
        }

        try:
            response = requests.get(proxy_url, params={"url": toptex_url}, headers=headers)

            if response.status_code == 200:
                products = response.json().get("products", [])
                for product in products:
                    default_code = product.get("sku")
                    name = product.get("name")
                    toptex_id = product.get("reference")

                    if not default_code or not toptex_id:
                        continue  # evita errores si faltan datos clave

                    existing = self.env["product.template"].search([
                        ("toptex_product_id", "=", toptex_id)
                    ], limit=1)

                    if existing:
                        continue  # ya existe

                    self.create({
                        "name": name,
                        "default_code": default_code,
                        "toptex_product_id": toptex_id,
                        "type": "product",
                    })
                _logger.info("✅ Productos sincronizados correctamente desde TopTex.")
            else:
                _logger.error(f"❌ Error de conexión: {response.status_code} - {response.text}")

        except Exception as e:
            _logger.exception(f"❌ Excepción al sincronizar productos: {e}")