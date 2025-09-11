import streamlit as st
import pandas as pd
import os
import logging
from datetime import datetime

LOG_DIR = "/home/pi/logs"
INFORMACION_CSV_FILE = "/home/pi/Desktop/Medidor/Dashboard/informacion.csv"

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'informacion_page_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_informacion():
    """Cargar datos desde el archivo CSV o devolver valores por defecto."""
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
                # Asegurar que todas las claves existan
                for key in default_data:
                    if key not in data or pd.isna(data[key]):
                        data[key] = default_data[key]
                logger.debug(f"Datos de información cargados: {data}")
                return data
        logger.warning(f"No existe {INFORMACION_CSV_FILE}, retornando valores por defecto")
        return default_data
    except Exception as e:
        logger.error(f"Error cargando {INFORMACION_CSV_FILE}: {e}", exc_info=True)
        return default_data
        

def save_informacion(data):
    """Guardar datos en el archivo CSV."""
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
        logger.info(f"Datos de información guardados en {INFORMACION_CSV_FILE}: {data}")
        st.toast("Configuración de información guardada correctamente")

    except Exception as e:
        logger.error(f"Error guardando {INFORMACION_CSV_FILE}: {e}", exc_info=True)
        st.error(f"Error guardando configuracion: {e}")

def run():
    st.title("Información")

    # Estilos CSS coherentes con el dashboard
    st.markdown("""
    <style>
    .info-container {
        background-color: #2a2a2a;
        border: 2px solid #555;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .info-container p {
        color: white;
        font-size: 16px;
        margin: 5px 0;
    }
    .config-button > button {
        background-color: #222222 !important;
        color: white !important;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 16px;
        margin-left: 10px;
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
    .stTextInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: #444444 !important;
        color: white !important;
        border-radius: 5px;
    }
    .centered-title {
        text-align: center;
        color: white;
        font-size: 24px;
        margin-bottom: 20px;
    }
    .gear-button {
        background-color: transparent;
        border: none;
        color: #999;
        cursor: pointer;
        font-size: 20px;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Cargar datos
    data = load_informacion()

    # Estado para controlar el formulario de edicion
    if 'show_config_informacion' not in st.session_state:
        st.session_state.show_config_informacion = False

    # Mostrar datos como texto estatico
    with st.container():
            
        with st.container():
            #st.markdown('<div class="info-container">', unsafe_allow_html=True)
            st.markdown(f"<p><b>Tí­tulo:</b> {data['titulo']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Titular:</b> {data['titular']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Dirección:</b> {data['direccion']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Tel. contacto:</b> {data['telefono_contacto']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>No. de servicio:</b> {data['no_servicio']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Tarifa CFE:</b> {data['tarifa_cfe']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>No. medidor:</b> {data['no_medidor']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>No. hilos:</b> {data['no_hilos']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p><b>Fecha de inicio:</b> {data['fecha_inicio']}</p>", unsafe_allow_html=True)
           
            with st.container():
                col1, col2 = st.columns([3, 1])  # Divide el espacio en 3:1, con col1 ocupando 3 partes y col2 1 parte
                with col1:
                    # Boton que ahora ocupa solo un cuarto del ancho
                    if st.button("CONFIGURAR", key="config_informacion", help="Configurar informacion"):
                        st.session_state.show_config_informacion = not st.session_state.show_config_informacion
                        logger.debug(f"Estado de show_config_informacion cambiado a: {st.session_state.show_config_informacion}")

                with col2:
                    pass

                   

            # Mostrar el formulario si el boton fue presionado
            if st.session_state.show_config_informacion:
                st.markdown('<h2 class="centered-title">Configurar Información</h2>', unsafe_allow_html=True)
                
                # Campos del formulario
                titulo = st.text_input("Título", value=data['titulo'] if data['titulo'] != 'No configurado' else '', key="titulo")
                titular = st.text_input("Titular", value=data['titular'] if data['titular'] != 'No configurado' else '', key="titular")
                direccion = st.text_input("Dirección", value=data['direccion'] if data['direccion'] != 'No configurado' else '', key="direccion")
                telefono_contacto = st.text_input("Tel. contacto", value=data['telefono_contacto'] if data['telefono_contacto'] != 'No configurado' else '', key="telefono_contacto")
                no_servicio = st.text_input("No. de servicio", value=data['no_servicio'] if data['no_servicio'] != 'No configurado' else '', key="no_servicio")
                tarifa_cfe = st.text_input("Tarifa CFE", value=data['tarifa_cfe'] if data['tarifa_cfe'] != 'No configurado' else '', key="tarifa_cfe")
                no_medidor = st.text_input("No. medidor", value=data['no_medidor'] if data['no_medidor'] != 'No configurado' else '', key="no_medidor")
                no_hilos = st.selectbox("No. hilos", options=[1, 2, 3], index=[1, 2, 3].index(data['no_hilos']) if data['no_hilos'] in [1, 2, 3] else 0, key="no_hilos")
                fecha_inicio = st.date_input("Fecha de inicio", value=datetime.strptime(data['fecha_inicio'], '%Y-%m-%d') if data['fecha_inicio'] != 'No configurado' else datetime.now(), key="fecha_inicio")

                # Boton de guardar dentro del div
                st.markdown('<div class="main-button">', unsafe_allow_html=True)
                if st.button("Guardar Configuración", key="save_informacion"):
                    new_data = {
                        'titulo': titulo if titulo else 'No configurado',
                        'titular': titular if titular else 'No configurado',
                        'direccion': direccion if direccion else 'No configurado',
                        'telefono_contacto': telefono_contacto if telefono_contacto else 'No configurado',
                        'no_servicio': no_servicio if no_servicio else 'No configurado',
                        'tarifa_cfe': tarifa_cfe if tarifa_cfe else 'No configurado',
                        'no_medidor': no_medidor if no_medidor else 'No configurado',
                        'no_hilos': no_hilos,
                        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d')
                    }
                    save_informacion(new_data)
                    st.session_state.show_config_informacion = False
                    st.rerun()
                    logger.info("Configuración de informacion guardada y seccion ocultada")

if __name__ == "__main__":
    run()
