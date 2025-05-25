import requests
from datetime import datetime, timedelta
import pytz
from odoo import models, fields

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de autenticación API'
    _rec_name = 'token'

    token = fields.Text(string='Token')
    expiry_time = fields.Datetime(string='Expira en')
    username = fields.Char(string='Usuario')
    password = fields.Char(string='Contraseña')

    def get_token(self):
        token_record = self.search([], limit=1, order='create_date desc')
        now = datetime.now(pytz.utc)

        if token_record and token_record.token and token_record.expiry_time > now:
            return token_record.token

        username = token_record.username if token_record else 'toes_bafaluydelreymarc'
        password = token_record.password if token_record else 'Bafarey12345.'
        api_key = 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgidvgiZe'

        url = 'https://api.toptex.io/v3/token'
        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        body = {
            'username': username,
            'password': password
        }

        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        token = token_data.get('token')
        expires_in = token_data.get('expires_in', 3600)

        expiry_time = now + timedelta(seconds=expires_in)

        self.create({
            'token': token,
            'expiry_time': expiry_time,
            'username': username,
            'password': password,
        })

        return token