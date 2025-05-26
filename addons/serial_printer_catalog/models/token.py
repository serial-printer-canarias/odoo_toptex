import requests
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de autenticación para API de TopTex'

    api_key = fields.Char(string='API Key', required=True)
    username = fields.Char(string='Usuario', required=True)
    password = fields.Char(string='Contraseña', required=True)
    token = fields.Text(string='Token')
    token_expiration = fields.Datetime(string='Expiración del Token')

    def get_valid_token(self):
        self.ensure_one()
        if self.token and self.token_expiration and self.token_expiration > fields.Datetime.now():
            return self.token
        else:
            return self.generate_token()

    def generate_token(self):
        self.ensure_one()

        url = 'https://api.toptex.io/v3/authenticate'
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'username': self.username,
            'password': self.password
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                expires_in = data.get('expires_in')

                if access_token and expires_in:
                    self.token = access_token
                    self.token_expiration = datetime.now() + timedelta(seconds=int(expires_in))
                    return self.token
                else:
                    raise UserError('Respuesta inválida de la API: faltan datos del token.')
            else:
                raise UserError(f'Error al obtener token: {response.status_code} - {response.text}')
        except Exception as e:
            raise UserError(f'Error al conectar con la API de TopTex: {str(e)}')