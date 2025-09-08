import streamlit as st
import json
import os
from datetime import datetime
import logging

LOG_DIR = "/home/pi/logs"
ALERTS_CONFIG_HOME = "/home/pi/Desktop/Medidor/Dashboard/alerts_config.json"
ALERTS_STORAGE_HOME = "/home/pi/Desktop/Medidor/Dashboard/alerts_storage.json"

CONFIG_VARIABLES = [
    'Corriente_linea1', 'Voltaje_fase_1', 'Potencia_activa_f1', 'Potencia_activa_Total',
    'Potencia_aparente_total', 'Factor_Potencia', 'frecuencia'
]

CONFIG_PARAMETROS = ['Corriente_linea1', 'Potencia_activa_Total', 'Potencia_aparente_total']
CONFIG_AVANZADA = ['frecuencia', 'Voltaje_fase_1', 'Factor_Potencia']

UNITS_PER_VARIABLE = {
    'Corriente_linea1': 'A',
    'Voltaje_fase_1': 'V',
    'Potencia_activa_f1': 'kW',
    'Potencia_activa_Total': 'kW',
    'Potencia_aparente_total': 'kVA',
    'Factor_Potencia': '',
    'frecuencia': 'Hz',
    'CPU': '%',
    'Disco_Uso': '%',
    'Disco_Libre': 'GB',
    'Temperatura': 'C'
}
PER_VARIABLE_NAME = {
    'Corriente_linea1': 'Corriente Linea 1',
    'Voltaje_fase_1': 'Voltaje Fase 1',
    'Potencia_activa_f1': 'Potencia Activa Fase 1',
    'Potencia_activa_Total': 'Potencia Activa Total',
    'Potencia_aparente_total': 'Potencia Aparente Total',
    'Factor_Potencia': 'Factor de Potencia',
    'frecuencia': 'Frecuencia',
    'CPU': 'Uso de CPU',
    'Disco_Uso': 'Uso de Disco',
    'Disco_Libre': 'Espacio Libre en Disco',
    'Temperatura': 'Temperatura',
    'Internet': 'Conexion a Internet',
    'Sistema': 'Sistema'
}

logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'alertas_page_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_alerts_config():
    try:
        with open(ALERTS_CONFIG_HOME, 'r') as f:
            config = json.load(f)
        logger.debug(f"ConfiguraciÃ³n de alertas cargada: {config}")
        return config
    except Exception as e:
        logger.error(f"Error cargando configuraciÃ³n de alertas: {e}", exc_info=True)
        return {var: {"min": None, "max": None} for var in CONFIG_VARIABLES}

def save_alerts_config(config):
    try:
        temp_file = ALERTS_CONFIG_HOME + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(config, f, indent=4)
        os.replace(temp_file, ALERTS_CONFIG_HOME)
        os.chmod(ALERTS_CONFIG_HOME, 0o664)
        logger.info(f"ConfiguraciÃ³n de alertas guardada en {ALERTS_CONFIG_HOME}: {config}")
        st.success("ConfiguraciÃ³n de alertas guardada correctamente")
    except Exception as e:
        logger.error(f"Error guardando configuraciÃ³n de alertas: {e}", exc_info=True)
        st.error(f"Error guardando configuraciÃ³n de alertas: {e}")

def load_alerts_storage():
    try:
        if os.path.exists(ALERTS_STORAGE_HOME):
            with open(ALERTS_STORAGE_HOME, 'r') as f:
                alerts = json.load(f)
            logger.debug(f"Alertas cargadas: {len(alerts)} alertas")
            return alerts
        else:
            logger.warning(f"No existe {ALERTS_STORAGE_HOME}")
            return []
    except Exception as e:
        logger.error(f"Error cargando almacenamiento de alertas: {e}", exc_info=True)
        return []
        

def save_alerts_storage(alerts):
    try:
        temp_file = ALERTS_STORAGE_HOME + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(alerts, f, indent=4)
        os.replace(temp_file, ALERTS_STORAGE_HOME)
        os.chmod(ALERTS_STORAGE_HOME, 0o664)
        user = os.getlogin()
        import pwd
        user_info = pwd.getpwnam(user)
        os.chown(ALERTS_STORAGE_HOME, user_info.pw_uid, user_info.pw_gid)
        logger.debug(f"Alertas guardadas: {len(alerts)} alertas en {ALERTS_STORAGE_HOME}")
    except Exception as e:
        logger.error(f"Error guardando alertas en {ALERTS_STORAGE_HOME}: {e}", exc_info=True)
        st.error(f"Error guardando alertas: {e}")

def delete_alert(index):
    alerts = load_alerts_storage()
    if 0 <= index < len(alerts):
        alerts.pop(index)
        save_alerts_storage(alerts)
        logger.info(f"Alerta en indice {index} eliminada")
        st.success(f"Alerta eliminada correctamente")
    else:
        logger.error(f"Ãndice de alerta {index} no valido")
        st.error("Error: Ãndice de alerta no vÃ¡lido")

def delete_all_alerts():
    try:
        save_alerts_storage([])
        logger.info("Todas las alertas eliminadas")
        st.success("Todas las alertas eliminadas correctamente")
    except Exception as e:
        logger.error(f"Error eliminando todas las alertas: {e}", exc_info=True)
        st.error(f"Error eliminando todas las alertas: {e}")

def run():
    st.title("Configurar Alertas")
    
    # BLOQUE DE CONFIGURACION DE COLORES
    # Aqui se definen los colores de los recuadros de las alertas
    # Cambia los valores de background-color para personalizar los colores
    st.markdown("""
    <style>
    /* Color para alertas de variables electricas (activa y finalizada, rojo oscuro) */
    .alert-container-electrical {
        background-color: #8B0000; /* Cambia este color para alertas de variables electricas */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Color para alerta de Sistema (activa y finalizada, verde) */
    .alert-container-system {
        background-color: #008000; /* Cambia este color para alerta de Sistema */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Color para alerta de Internet (solo finalizada, azul cielo) */
    .alert-container-internet {
        background-color: #2EC0FF; /* Cambia este color para alerta de Internet finalizada */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Color para alertas de CPU y Uso de Disco (activa y finalizada, naranja) */
    .alert-container-cpu-disk {
        background-color: #A65C02; /* Cambia este color para alertas de CPU y Uso de Disco */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Color para alertas de Espacio Libre en Disco (activa y finalizada, azul rey) */
    .alert-container-disk-free {
        background-color: #0000A3; /* Cambia este color para alertas de Espacio Libre en Disco */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    /* Color para alertas de Temperatura (activa y finalizada, amarillo) */
    .alert-container-temperature {
        background-color: #FFFF00; /* Cambia este color para alertas de Temperatura */
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .alert-container-electrical p, .alert-container-system p, .alert-container-internet p, .alert-container-cpu-disk p, .alert-container-disk-free p, .alert-container-temperature p {
        margin: 0;
        color: white;
        font-size: 14px;
        text-align: center;
        flex-grow: 1;
    }
    .alert-container-electrical .stButton > button, .alert-container-system .stButton > button, .alert-container-internet .stButton > button, .alert-container-cpu-disk .stButton > button, .alert-container-disk-free .stButton > button, .alert-container-temperature .stButton > button {
        background-color: #0E7500 !important;
        color: black !important;
        border-radius: 5px;
        padding: 5px 10px;
        font-size: 12px;
    }
    .config-section {
        background-color: #2a2a2a;
        border: 2px solid #555;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
    }
    .config-section h3 {
        color: white;
        font-size: 18px;
        margin-bottom: 10px;
    }
    .stNumberInput > div > div > input {
        background-color: #444444 !important;
        color: white !important;
        border-radius: 5px;
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
    .header-container {
        background-color: #111111;
        border: 2px solid #555;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .header-container p {
        margin: 0;
        color: white;
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        flex-grow: 1;
    }
    .centered-title {
        text-align: center;
        color: white;
        font-size: 24px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    # FIN DEL BLOQUE DE CONFIGURACION DE COLORES

    st.header("Lista de Alertas")
    alerts = load_alerts_storage()
    
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        with col1:
            st.markdown('<div class="header-container"><p>DescripciÃ³n</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="header-container"><p>Valor</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="header-container"><p>Fecha de Inicio</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="header-container"><p>Fecha Final</p></div>', unsafe_allow_html=True)
        with col5:
            st.markdown('<div style="height: 38px;"></div>', unsafe_allow_html=True)

    if not alerts:
        st.info("No hay alertas registradas.")
        logger.debug("No hay alertas para mostrar")
    else:
        # BLOQUE DE ASIGNACION DE COLORES PARA ALERTAS
        # Aqui se asigna la clase CSS segun el tipo de alerta
        for i, alert in enumerate(alerts):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                message = alert['message']
                value = f"{alert['value']:.2f} {UNITS_PER_VARIABLE.get(alert['variable'], '')}" if alert['value'] is not None else ("--" if alert['variable'] in ["Sistema", "Internet"] else "N/A")
                start_time = alert['start_time']
                end_time = alert.get('end_time', 'Activa')
                if alert['variable'] in CONFIG_VARIABLES:
                    container_class = "alert-container-electrical"
                elif alert['variable'] == "Sistema":
                    container_class = "alert-container-system"
                elif alert['variable'] == "Internet":
                    container_class = "alert-container-internet"
                elif alert['variable'] in ["CPU", "Disco_Uso"]:
                    container_class = "alert-container-cpu-disk"
                elif alert['variable'] == "Disco_Libre":
                    container_class = "alert-container-disk-free"
                elif alert['variable'] == "Temperatura":
                    container_class = "alert-container-temperature"
                with col1:
                    st.markdown(f'<div class="{container_class}"><p>{message}</p></div>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<div class="{container_class}"><p>{value}</p></div>', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'<div class="{container_class}"><p>{start_time}</p></div>', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'<div class="{container_class}"><p>{end_time}</p></div>', unsafe_allow_html=True)
                with col5:
                    if st.button("Borrar", key=f"delete_alert_{i}"):
                        delete_alert(i)
                        st.rerun()
        # FIN DEL BLOQUE DE ASIGNACION DE COLORES PARA ALERTAS

    with st.container():
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Borrar Todas las Alertas"):
            delete_all_alerts()
            st.rerun()
        if st.button("ConfiguraciÃ³n de parametros"):
            st.session_state.show_config_parametros = not st.session_state.get('show_config_parametros', False)
            st.session_state.show_config_avanzada = False
            logger.debug(f"Estado de show_config_parametros cambiado a: {st.session_state.get('show_config_parametros')}")
        if st.button("ConfiguraciÃ³n avanzada"):
            st.session_state.show_config_avanzada = not st.session_state.get('show_config_avanzada', False)
            st.session_state.show_config_parametros = False
            logger.debug(f"Estado de show_config_avanzada cambiado a: {st.session_state.get('show_config_avanzada')}")
        st.markdown('</div>', unsafe_allow_html=True)

    if 'show_config_parametros' not in st.session_state:
        st.session_state.show_config_parametros = False
    if 'show_config_avanzada' not in st.session_state:
        st.session_state.show_config_avanzada = False

    if st.session_state.show_config_parametros:
        st.markdown('<div class="config-section">', unsafe_allow_html=True)
        st.markdown('<h2 class="centered-title">ConfiguraciÃ³n de parametros</h2>', unsafe_allow_html=True)
        config = load_alerts_config()
        for variable in CONFIG_PARAMETROS:
            st.subheader(f"{PER_VARIABLE_NAME[variable]} ({UNITS_PER_VARIABLE.get(variable, '')})")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(
                    f"Minimo permitido",
                    value=config[variable]['min'] if config[variable]['min'] is not None else 0.0,
                    step=0.1,
                    key=f"min_{variable}",
                    format="%.2f"
                )
            with col2:
                max_val = st.number_input(
                    f"Maximo permitido",
                    value=config[variable]['max'] if config[variable]['max'] is not None else 100.0,
                    step=0.1,
                    key=f"max_{variable}",
                    format="%.2f"
                )
            config[variable] = {"min": min_val, "max": max_val}
        
        with st.container():
            st.markdown('<div class="main-button">', unsafe_allow_html=True)
            if st.button("Guardar ConfiguraciÃ³n", key="save_config_parametros"):
                save_alerts_config(config)
                st.session_state.show_config_parametros = False
                st.rerun()
                logger.info("ConfiguraciÃ³n de parametros guardada y seccion ocultada")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.show_config_avanzada:
        st.markdown('<div class="config-section">', unsafe_allow_html=True)
        st.markdown('<h2 class="centered-title">ConfiguraciÃ³n preestablecida de acuerdo a normativa de Codigo de Red</h2>', unsafe_allow_html=True)
        config = load_alerts_config()
        for variable in CONFIG_AVANZADA:
            st.subheader(f"{PER_VARIABLE_NAME[variable]} ({UNITS_PER_VARIABLE.get(variable, '')})")
            col1, col2 = st.columns(2)
            with col1:
                min_val = st.number_input(
                    f"Minimo permitido",
                    value=config[variable]['min'] if config[variable]['min'] is not None else 0.0,
                    step=0.1,
                    key=f"min_{variable}",
                    format="%.2f"
                )
            with col2:
                max_val = st.number_input(
                    f"Maximo permitido",
                    value=config[variable]['max'] if config[variable]['max'] is not None else 100.0,
                    step=0.1,
                    key=f"max_{variable}",
                    format="%.2f"
                )
            config[variable] = {"min": min_val, "max": max_val}
        
        with st.container():
            st.markdown('<div class="main-button">', unsafe_allow_html=True)
            if st.button("Guardar ConfiguraciÃ³n", key="save_config_avanzada"):
                save_alerts_config(config)
                st.session_state.show_config_avanzada = False
                st.rerun()
                logger.info("ConfiguraciÃ³n avanzada guardada y seccion ocultada")
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    run()
