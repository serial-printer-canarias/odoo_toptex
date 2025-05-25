import requests
from odoo import models, fields, api

class SerialPrinterProduct(models.Model):
    _name = 'serial.printer.product'
    _description = 'Producto importado desde API'

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
                'name': 'Sincronizar productos',
                'type': 'server',
                'level': 'WARNING',
                'message': 'Token no disponible. Abortando sincronización.',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 21,
            })
            return

        token = token_obj.token
        url = 'https://api.toptex.io/v3/products'

        headers = {
            'Authorization': f'Bearer {token}',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4b0vgiZe'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data:
                _logger = self.env['ir.logging']
                _logger.create({
                    'name': 'Sincronizar productos',
                    'type': 'server',
                    'level': 'WARNING',
                    'message': 'Respuesta vacía al solicitar productos',
                    'path': __file__,
                    'func': 'sync_products_from_api',
                    'line': 43,
                })
                return

            for item in data:
                self.env['serial.printer.product'].create({
                    'name': item.get('name'),
                    'toptex_id': item.get('id'),
                    'description': item.get('description', ''),
                })

        except requests.exceptions.HTTPError as e:
            _logger = self.env['ir.logging']
            _logger.create({
                'name': 'Sincronizar productos',
                'type': 'server',
                'level': 'ERROR',
                'message': f'Error {response.status_code}: {response.text}',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 58,
            })
        except Exception as e:
            _logger = self.env['ir.logging']
            _logger.create({
                'name': 'Sincronizar productos',
                'type': 'server',
                'level': 'ERROR',
                'message': f'Error inesperado: {str(e)}',
                'path': __file__,
                'func': 'sync_products_from_api',
                'line': 67,
            })