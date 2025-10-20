import subprocess
import json
import time
import os
import smtplib
from email.mime.text import MIMEText
import logging

# Configuracion
NGROK_API = "http://localhost:4040/api/tunnels"
NGROK_URL_FILE = '/home/pi/ngrok_url.txt'
INVITADOS_FILE = "/home/pi/invitados.txt"
CHECK_INTERVAL = 300  # 5 minutos

SENDER_ADDRESS = "aradilla3nueces@gmail.com"
SENDER_PASSWORD = "uulf ovmx emdz icaa"
SENDER_SERVER = 'smtp.gmail.com'
SENDER_PORT = 587

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Funciones
def get_ngrok_url():
    try:
        result = subprocess.run(
            ["curl", "-s", NGROK_API],
            capture_output=True, text=True, check=True
        )
        tunnels = json.loads(result.stdout)
        return tunnels["tunnels"][0]["public_url"]
    except Exception as e:
        logging.error(f"Error obteniendo URL de ngrok: {e}")
        return None

def read_last_url():
    if os.path.exists(NGROK_URL_FILE):
        with open(NGROK_URL_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_url(url):
    with open(NGROK_URL_FILE, 'w') as f:
        f.write(url)

def cargar_invitados():
    if os.path.exists(INVITADOS_FILE):
        with open(INVITADOS_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def enviar_correo(destinatario, asunto, cuerpo):
    try:
        msg = MIMEText(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = SENDER_ADDRESS
        msg['To'] = destinatario

        with smtplib.SMTP(SENDER_SERVER, SENDER_PORT) as server:
            server.starttls()
            server.login(SENDER_ADDRESS, SENDER_PASSWORD)
            server.send_message(msg)

        logging.info(f"Correo enviado a {destinatario}")
    except Exception as e:
        logging.error(f"Error enviando correo a {destinatario}: {e}")

def enviar_a_invitados(url):
    invitados = cargar_invitados()
    if not invitados:
        logging.info("No hay invitados.")
        return
    asunto = "Nueva URL de acceso a la plataforma"
    cuerpo = (
        f"Hola,\n\n"
        f"Tu nueva URL de acceso es:\n{url}\n\n"
        f"Por favor guardala para futuros accesos.\n\n"
        f"Equipo de Monitoreo Energetico"
    )
    for destinatario in invitados:
        enviar_correo(destinatario, asunto, cuerpo)

def main():
    logging.info("Iniciando monitor automatico de ngrok...")
    while True:
        current_url = get_ngrok_url()
        if current_url:
            last_url = read_last_url()
            if current_url != last_url:
                logging.info(f"URL de ngrok cambio: {last_url} -> {current_url}")
                save_url(current_url)
                enviar_a_invitados(current_url)
            else:
                logging.info("La URL no ha cambiado.")
        else:
            logging.warning("No se pudo obtener la URL de ngrok.")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
