# models/token.py

import requests
from datetime import datetime, timedelta
from odoo import models, fields, api
import pytz

class SerialPrinterToken(models.Model):
    _name = 'serial.printer.token'
    _description = 'Token de Autenticación API TopTex'

    token = fields.Text(string='Token')
    expiry_time = fields.Datetime(string='Caducidad')
    username = fields.Char(string='Usuario')
    password = fields.Char(string='Contraseña')

    def get_valid_token(self):
        """Retorna un token válido o genera uno nuevo si caducó."""
        record = self.search([], limit=1, order="expiry_time desc")
        now = datetime.now(pytz.utc)

        if record and record.token and record.expiry_time > now:
            return record.token
        else:
            return self.generate_new_token()

    def generate_new_token(self):
        """Genera un nuevo token desde la API de TopTex y lo guarda."""
        url = "https://api.toptex.io/v3/login"
        record = self.search([], limit=1, order="expiry_time desc")

        if not record or not record.username or not record.password:
            raise ValueError("Credenciales de API no configuradas.")

        headers = {"x-api-key": "qh7SERVyz43xDDNaRoNs0aLxGnTtfSOX4bOvgizEdvgiZe"}
        payload = {
            "username": record.username,
            "password": record.password
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("token")
            expiry = datetime.now(pytz.utc) + timedelta(hours=1)

            record.write({
                'token': token,
                'expiry_time': expiry,
            })

            return token
        else:
            raise ValueError("Error al obtener token: " + response.text)