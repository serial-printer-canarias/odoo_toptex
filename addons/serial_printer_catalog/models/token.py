# models/token.py
import requests
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import UserError

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de Autenticación TopTex'

    token = fields.Text(string='Token')
    expiration = fields.Datetime(string='Fecha de expiración')
    api_user = fields.Char(string='Usuario API', default='toes_bafaluydelreymarc')
    api_password = fields.Char(string='Contraseña API', default='Bafarey12345.')
    api_key = fields.Char(string='API Key', default='qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizEdvgiZe')

    def get_valid_token(self):
        self.ensure_one()
        now = datetime.now()
        if self.token and self.expiration and self.expiration > now + timedelta(minutes=5):
            return self.token

        url = 'https://api.toptex.io/auth'
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'username': self.api_user,
            'password': self.api_password
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token')
            if not token:
                raise UserError('La respuesta de autenticación no contiene token.')
            self.token = token
            self.expiration = now + timedelta(hours=1)
            return token
        else:
            raise UserError(f'Error al obtener token: {response.text}')