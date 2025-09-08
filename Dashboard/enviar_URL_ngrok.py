import subprocess
import json
import time
import smtplib
from email.mime.text import MIMEText
import logging
import os

# Configuracion de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuracion del correo
SENDER_ADDRESS = "solucionesenergiainnovacion@gmail.com"
SENDER_PASSWORD = "psvx asnh vluc rglh"
SENDER_SERVER = 'smtp.gmail.com'
SENDER_PORT = 587
RECIPIENT_ADDRESS = "solucionesenergiainnovacion@gmail.com"

# Archivo para almacenar la ultima URL
URL_FILE = '/home/pi/ngrok_url.txt'

def get_ngrok_url():
    """Obtiene la URL publica de Ngrok."""
    try:
        # Esperar a que Ngrok este listo
        time.sleep(5)
        # Ejecutar curl para obtener los tuneles
        result = subprocess.run(
            ["curl", "-s", "http://localhost:4040/api/tunnels"],
            capture_output=True, text=True, check=True
        )
        # Parsear el JSON y extraer la URL
        tunnels = json.loads(result.stdout)
        url = tunnels["tunnels"][0]["public_url"]
        logging.info(f"Ngrok URL obtenida: {url}")
        return url
    except Exception as e:
        logging.error(f"Error al obtener la URL de Ngrok: {e}")
        return None

def send_email(url):
    """Envia la URL de Ngrok por correo."""
    try:
        # Crear el mensaje
        msg = MIMEText(f"La URL de Ngrok para acceder al Dashboard es: {url}")#------------------------------------------------
        msg['From'] = SENDER_ADDRESS
        msg['To'] = RECIPIENT_ADDRESS
        msg['Subject'] = 'URL de Ngrok para el Dashboard'#-----------------------------------------------

        # Enviar el correo
        with smtplib.SMTP(SENDER_SERVER, SENDER_PORT) as server:
            server.starttls()
            server.login(SENDER_ADDRESS, SENDER_PASSWORD)
            server.sendmail(SENDER_ADDRESS, RECIPIENT_ADDRESS, msg.as_string())
        logging.info("Correo con la URL de Ngrok enviado con exito")
    except Exception as e:
        logging.error(f"Error al enviar el correo: {e}")

def read_last_url():
    """Lee la ultima URL almacenada en el archivo."""
    try:
        if os.path.exists(URL_FILE):
            with open(URL_FILE, 'r') as f:
                return f.read().strip()
        return None
    except Exception as e:
        logging.error(f"Error al leer la ultima URL: {e}")
        return None

def save_url(url):
    """Guarda la URL en el archivo."""
    try:
        with open(URL_FILE, 'w') as f:
            f.write(url)
    except Exception as e:
        logging.error(f"Error al guardar la URL: {e}")

def main():
    while True:
        # Obtener la URL actual de Ngrok
        current_url = get_ngrok_url()
        
        if current_url:
            # Leer la ultima URL conocida
            last_url = read_last_url()
            
            # Comparar URLs
            if current_url != last_url:
                logging.info(f"URL cambiada de {last_url} a {current_url}")
                # Guardar la nueva URL
                save_url(current_url)
                # Enviar correo con la nueva URL
                send_email(current_url)
            else:
                logging.debug("La URL no ha cambiado")
        else:
            logging.error("No se pudo obtener la URL de Ngrok")
        
        # Esperar antes de la proxima verificacion
        time.sleep(300)  # Verificar cada 5 minutos

if __name__ == "__main__":
    main()
