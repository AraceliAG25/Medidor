import streamlit as st
import pandas as pd
import os
import logging
from datetime import datetime

import subprocess
import json
import time


# -------------------------- Configuracion general --------------------------
NGROK_API = "http://localhost:4040/api/tunnels"#---------------------
NGROK_URL_FILE = '/home/pi/ngrok_url.txt'

LOG_DIR = "/home/pi/logs"
INFORMACION_CSV_FILE = "/home/pi/Desktop/Medidor/Dashboard/informacion.csv"
INVITADOS_FILE = "/home/pi/invitados.txt"
CHECK_INTERVAL = 300  # segundos (5 minutos) "-------------

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')#--------------

# Crear carpeta de logs si no existe
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'informacion_page_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# -------------------------- Funciones auxiliares --------------------------

import smtplib
from email.mime.text import MIMEText
import logging
import os  # Para obtener la contrasea de forma segura



# Datos del servidor SMTP
SENDER_ADDRESS = "aradilla3nueces@gmail.com"
SENDER_PASSWORD = "uulf ovmx emdz icaa" # O directamente en texto plano (no recomendado)
SENDER_SERVER = 'smtp.gmail.com'
SENDER_PORT = 587

# Funcin para enviar correos
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

        logging.info(f"Correo enviado a: {destinatario}")
    except Exception as e:
        logging.error(f"Error al enviar correo a {destinatario}: {e}")
        raise
def enviar_a_invitados(url):
    invitados = cargar_invitados()
    if not invitados:
        logging.warning("No hay invitados a quienes enviar el correo.")
        return

    asunto = "Nueva URL de acceso a la plataforma"
    cuerpo = (
        f"Hola, espero que te encuentres bien.\n\n"
        f"Ha cambiado la URL de acceso a la plataforma de monitoreo.\n\n"
        f"Tu nueva URL es: {url}\n\n"
        f"Por favor, guurdala para futuros accesos.\n\n"
        "Equipo de Monitoreo Energético"
    )

    for destinatario in invitados:
        enviar_correo(destinatario, asunto, cuerpo)
def get_ngrok_url():
    try:
        result = subprocess.run(
            ["curl", "-s", NGROK_API],
            capture_output=True, text=True, check=True
        )
        tunnels = json.loads(result.stdout)
        url = tunnels["tunnels"][0]["public_url"]
        logging.info(f"Ngrok URL actual: {url}")
        return url
    except Exception as e:
        logging.error(f"Error al obtener URL de Ngrok: {e}")
        return None
def read_last_url():
    if os.path.exists(NGROK_URL_FILE):
        with open(NGROK_URL_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_url(url):
    with open(NGROK_URL_FILE, 'w') as f:
        f.write(url)

def load_informacion():
    default_data = {
        'titulo': 'No configurado',
        'titular': 'No configurado',
        'direccion': 'No configurado',
        'telefono_contacto': 'No configurado',
        'no_servicio': 'No configurado',
        'tarifa_cfe': 'No configurado',
        'no_medidor': 'No configurado',
        'no_hilos': 1,
        'fecha_inicio': 'No configurado'
    }
    try:
        if os.path.exists(INFORMACION_CSV_FILE):
            df = pd.read_csv(INFORMACION_CSV_FILE)
            if not df.empty:
                data = df.iloc[0].to_dict()
                for key in default_data:
                    if key not in data or pd.isna(data[key]):
                        data[key] = default_data[key]
                logger.debug(f"Datos cargados: {data}")
                return data
        logger.warning(f"No existe {INFORMACION_CSV_FILE}, usando valores por defecto")
        return default_data
    except Exception as e:
        logger.error(f"Error cargando {INFORMACION_CSV_FILE}: {e}", exc_info=True)
        return default_data


def save_informacion(data):
    try:
        temp_file = INFORMACION_CSV_FILE + '.tmp'
        df = pd.DataFrame([data])
        df.to_csv(temp_file, index=False)
        os.replace(temp_file, INFORMACION_CSV_FILE)
        os.chmod(INFORMACION_CSV_FILE, 0o664)
        user = os.getlogin()
        import pwd
        user_info = pwd.getpwnam(user)
        os.chown(INFORMACION_CSV_FILE, user_info.pw_uid, user_info.pw_gid)
        logger.info(f"Datos guardados en {INFORMACION_CSV_FILE}: {data}")
        st.toast("Configuracion guardada correctamente")
    except Exception as e:
        logger.error(f"Error guardando {INFORMACION_CSV_FILE}: {e}", exc_info=True)
        st.error(f"Error al guardar: {e}")

# -------------------------- Invitados --------------------------

def cargar_invitados():
    if os.path.exists(INVITADOS_FILE):
        with open(INVITADOS_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def guardar_invitado(correo):
    with open(INVITADOS_FILE, 'a') as f:
        f.write(correo.strip() + '\n')

def borrar_invitados():
    if os.path.exists(INVITADOS_FILE):
        os.remove(INVITADOS_FILE)

# -------------------------- Interfaz Streamlit --------------------------

def run():
    st.title("Informacion")

    # Estilos personalizados
    st.markdown("""
    <style>
    .centered-title {
        text-align: center;
        color: white;
        font-size: 24px;
        margin-bottom: 20px;
    }
    .main-button > button {
        background-color: #222222 !important;
        color: white !important;
        border-radius: 5px;
        width: 200px !important;
        margin: 10px auto !important;
        display: block !important;
        padding: 5px 10px !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------- Mostrar informacion ----------
    data = load_informacion()
    if 'show_config_informacion' not in st.session_state:
        st.session_state.show_config_informacion = False

    with st.container():
        st.markdown(f"**Titulo:** {data['titulo']}")
        st.markdown(f"**Titular:** {data['titular']}")
        st.markdown(f"**Direccion:** {data['direccion']}")
        st.markdown(f"**Tel. contacto:** {data['telefono_contacto']}")
        st.markdown(f"**No. de servicio:** {data['no_servicio']}")
        st.markdown(f"**Tarifa CFE:** {data['tarifa_cfe']}")
        st.markdown(f"**No. medidor:** {data['no_medidor']}")
        st.markdown(f"**No. hilos:** {data['no_hilos']}")
        st.markdown(f"**Fecha de inicio:** {data['fecha_inicio']}")

        if st.button("CONFIGURAR"):
            st.session_state.show_config_informacion = not st.session_state.show_config_informacion

        if st.session_state.show_config_informacion:
            st.markdown('<h2 class="centered-title">Configurar Informacion</h2>', unsafe_allow_html=True)
            titulo = st.text_input("Titulo", value=data['titulo'] if data['titulo'] != 'No configurado' else '')
            titular = st.text_input("Titular", value=data['titular'] if data['titular'] != 'No configurado' else '')
            direccion = st.text_input("Direccion", value=data['direccion'] if data['direccion'] != 'No configurado' else '')
            telefono = st.text_input("Tel. contacto", value=data['telefono_contacto'] if data['telefono_contacto'] != 'No configurado' else '')
            servicio = st.text_input("No. de servicio", value=data['no_servicio'] if data['no_servicio'] != 'No configurado' else '')
            tarifa = st.text_input("Tarifa CFE", value=data['tarifa_cfe'] if data['tarifa_cfe'] != 'No configurado' else '')
            medidor = st.text_input("No. medidor", value=data['no_medidor'] if data['no_medidor'] != 'No configurado' else '')
            hilos = st.selectbox("No. hilos", options=[1, 2, 3], index=[1, 2, 3].index(data['no_hilos']) if data['no_hilos'] in [1, 2, 3] else 0)
            fecha_inicio = st.date_input("Fecha de inicio", value=datetime.strptime(data['fecha_inicio'], '%Y-%m-%d') if data['fecha_inicio'] != 'No configurado' else datetime.now())

            if st.button("Guardar Configuracion"):
                new_data = {
                    'titulo': titulo or 'No configurado',
                    'titular': titular or 'No configurado',
                    'direccion': direccion or 'No configurado',
                    'telefono_contacto': telefono or 'No configurado',
                    'no_servicio': servicio or 'No configurado',
                    'tarifa_cfe': tarifa or 'No configurado',
                    'no_medidor': medidor or 'No configurado',
                    'no_hilos': hilos,
                    'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d')
                }
                save_informacion(new_data)
                st.session_state.show_config_informacion = False
                st.rerun()

    st.markdown("---")
    st.header("Invitar personas a la plataforma")

    # ---------- Gestin de invitados ----------
    invitados = cargar_invitados()

    with st.form("invitar_formulario"):
        contacto = st.text_input("Correo electropnico o numero de telefono", placeholder="ej. ejemplo@correo.com o 5551234567")
        submitted = st.form_submit_button("Agregar")

        if submitted:
            if contacto.strip():
                guardar_invitado(contacto.strip())
                st.success(f"Agregado: {contacto}")
                st.rerun()
            else:
                st.warning("El campo est vaco")

    invitados = cargar_invitados()
    if invitados:
        st.markdown("### Lista de usuarios actuales")
        for idx, item in enumerate(invitados, start=1):
            st.write(f"{idx}. {item}")

        col1, col2 = st.columns(2)

        with col1:
            ngrok_url = get_ngrok_url()  # <-- obtenemos la URL dinamica
            if st.button("Enviar enlace"):
                asunto = "Url de plataforma de Monitoreo"
                cuerpo = (
                            f"Hola, espero que te encuentres bien.\n\n"
                            f"A partir de ahora recibirás un enlace para acceder a la plataforma de Monitoreo.\n\n"
                            f"Tu enlace de acceso es: {ngrok_url}\n\n"
                            "Por favor, guardalo para futuros accesos.\n\n"
                            "Atentamente,\n"
                            "Equipo de Monitoreo Energético"
                        )

                errores = []

                for destinatario in invitados:
                    try:
                        enviar_correo(destinatario, asunto, cuerpo)
                    except Exception as e:
                        errores.append(f"{destinatario}: {str(e)}")

                if errores:
                    st.error(f"Errores al enviar correos: {', '.join(errores)}")
                else:
                    st.success("Enlaces enviados correctamente.")

        with col2:
            if st.button("Borrar lista de invitados"):
                borrar_invitados()
                st.success("Lista de invitados eliminada.")
                st.rerun()
# -------------------------- Ejecutar App --------------------------

if __name__ == "__main__":
    run()
