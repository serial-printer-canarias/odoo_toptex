import requests
from datetime import datetime, timedelta
import pytz
from odoo import models, fields, api

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de autenticación API TopTex'
    _rec_name = 'username'

    token = fields.Char(string='Token')
    expiry_time = fields.Datetime(string='Expira en')
    username = fields.Char(string='Usuario')
    password = fields.Char(string='Contraseña')

    def get_valid_token(self):
        """ Devuelve un token válido desde la base de datos o solicita uno nuevo si ha expirado """
        record = self.search([], limit=1)
        now = datetime.now(pytz.timezone('Europe/Madrid'))

        if record and record.token and record.expiry_time and record.expiry_time > now:
            return record.token

        # Si no hay token válido, solicitar uno nuevo
        url = 'https://api.toptex.io/auth'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgidvgiZe'
        }
        data = {
            'username': record.username,
            'password': record.password
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            new_token = token_data.get('token')
            expiry_minutes = 60
            expiry_time = now + timedelta(minutes=expiry_minutes)

            record.write({
                'token': new_token,
                'expiry_time': expiry_time
            })
            return new_token
        else:
            raise Exception(f"Error al obtener token: {response.text}")