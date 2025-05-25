import requests
from datetime import datetime, timedelta
import pytz
from odoo import models, fields, api

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de autenticación API TopTex'
    _rec_name = 'token'

    token = fields.Text(string='Token')
    expiry_time = fields.Datetime(string='Expira')
    username = fields.Char(string='Usuario')
    password = fields.Char(string='Contraseña')

    def get_token(self):
        token_record = self.search([], limit=1, order="id desc")
        now = datetime.now(pytz.utc)

        if token_record and token_record.token and token_record.expiry_time and token_record.expiry_time > now + timedelta(minutes=5):
            return token_record.token

        # Si no hay token válido, obtener uno nuevo
        username = token_record.username if token_record else 'toes_bafaluydelreymarc'
        password = token_record.password if token_record else 'Bafarey12345.'
        api_key = 'qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4b0vgiZe'

        url = 'https://api.toptex.io/v3/token'

        headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }

        payload = {
            'username': username,
            'password': password
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            expiry_str = data.get('expiry_time')
            expiry = datetime.strptime(expiry_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc)

            if token:
                # Crear o actualizar el token
                if token_record:
                    token_record.write({
                        'token': token,
                        'expiry_time': expiry,
                    })
                else:
                    self.create({
                        'username': username,
                        'password': password,
                        'token': token,
                        'expiry_time': expiry,
                    })
                return token
            else:
                raise Exception("Token no recibido correctamente")

        raise Exception(f"Error al obtener token: {response.status_code} - {response.text}")