import requests
from odoo import models, fields, api

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado desde API TopTex'

    name = fields.Char(string='Nombre')
    toptex_id = fields.Char(string='ID TopTex')
    description = fields.Text(string='Descripción')

    @api.model
    def sync_products_from_api(self):
        # Buscar el token más reciente
        token_obj = self.env['serial.printer.token'].search([], order='create_date desc', limit=1)
        if not token_obj or not token_obj.token:
            _logger = self.env['ir.logging']
            _logger.create({
                'name': 'Sincronizar productos desde API',
                'type': 'server',
                'level': 'WARNING',
                'message': 'Token no disponible',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 16,
            })
            return

        token = token_obj.token
        url = 'https://api.toptex.io/v2/products'

        headers = {
            'Authorization': f'Bearer {token}',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizE',
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                self.env['ir.logging'].create({
                    'name': 'Sincronizar productos desde API',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': 'Respuesta vacía de la API',
                    'path': __file__,
                    'func': 'sync_products_from_api',
                    'line': 34,
                })
                return

            for item in data:
                self.env['serial.printer.product'].create({
                    'name': item.get('name', 'Sin nombre'),
                    'toptex_id': item.get('id'),
                    'description': item.get('description', ''),
                })

        except requests.exceptions.HTTPError as http_err:
            self.env['ir.logging'].create({
                'name': 'Sincronizar productos desde API',
                'type': 'server',
                'level': 'ERROR',
                'message': f'Error HTTP: {http_err}',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 51,
            })
        except Exception as e:
            self.env['ir.logging'].create({
                'name': 'Sincronizar productos desde API',
                'type': 'server',
                'level': 'ERROR',
                'message': f'Error inesperado: {e}',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 59,
            })