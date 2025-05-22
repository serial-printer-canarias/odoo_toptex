import requests
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto sincronizado de catálogo'

    name = fields.Char(string="Nombre", required=True)
    toptex_id = fields.Char(string="ID TopTex", required=True, index=True)
    ref = fields.Char(string="Referencia")
    description = fields.Text(string="Descripción")
    price = fields.Float(string="Precio")
    stock = fields.Integer(string="Stock")

    def get_toptex_token(self):
        auth_url = "https://api.toptex.io/v3/authenticate"
        auth_payload = {
            "username": "toes_bafaluydelreymarc",
            "password": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgiZe"
        }

        try:
            response = requests.post(auth_url, json=auth_payload)
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    return token
                else:
                    raise Exception("No se recibió el token en la respuesta.")
            else:
                raise Exception(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            _logger.error("Error al autenticar con la API de TopTex: %s", str(e))
            return None

    def sync_products_from_api(self):
        token = self.get_toptex_token()
        if not token:
            _logger.error("No se pudo obtener el token de autenticación. Abortando sincronización.")
            return

        url = "https://api.toptex.io/api/products"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        _logger.warning(">>>> Llamando a API TopTex con headers: %s", headers)

        try:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Error {response.status_code}: {response.text}")

            data = response.json()

            for item in data.get("items", []):
                product_id = item.get("id")
                name = item.get("name", "")
                ref = item.get("reference", "")
                description = item.get("description", "")
                price = item.get("price", {}).get("net", 0.0)
                stock = item.get("stock", {}).get("total", 0)

                existing_product = self.search([('toptex_id', '=', product_id)], limit=1)

                if existing_product:
                    existing_product.write({
                        'name': name,
                        'ref': ref,
                        'description': description,
                        'price': price,
                        'stock': stock,
                    })
                else:
                    self.create({
                        'toptex_id': product_id,
                        'name': name,
                        'ref': ref,
                        'description': description,
                        'price': price,
                        'stock': stock,
                    })

            _logger.warning(">>>> Sincronización de productos completada con éxito.")

        except Exception as e:
            _logger.error("Error al sincronizar productos desde API TopTex: %s", str(e))
            raise