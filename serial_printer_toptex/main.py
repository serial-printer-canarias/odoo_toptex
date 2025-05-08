# lógica de conexión con Toptex
import requests

def fetch_toptex_brands():
    url = "https://api.toptex.com/v2/brands"
    headers = {
        "X-AUTH-TOKEN": "AQUÍ_TU_TOKEN",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error al conectar con Toptex: {response.status_code} - {response.text}")