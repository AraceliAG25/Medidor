# -*- coding: utf-8 -*-
"""
estadisticas_page.py
--------------------
Proposito: Pagina de Streamlit para seleccionar variables y fechas, iniciar el procesamiento estadistico,
y mostrar los resultados del archivo Excel mas reciente.
"""

import streamlit as st
import pandas as pd
import os
import subprocess
import logging
import re
import glob
import pickle
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from data_collector import VARIABLES, VARIABLES_DISPLAY
from config import BASE_DIR, LOG_DIR, STATISTICS_CONFIG_FILE, STATISTICS_OUTPUT_DIR

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'estadisticas_page_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_statistics_config(variables, start_date, end_date, decimation_factor):
    """Guarda la configuracion de estadisticas en un archivo pickle."""
    try:
        os.makedirs(os.path.dirname(STATISTICS_CONFIG_FILE), exist_ok=True)
        data = {
            'variables': variables,
            'start_date': start_date,
            'end_date': end_date,
            'decimation_factor': decimation_factor,
            'processing': True,
            'error': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(STATISTICS_CONFIG_FILE, 'wb') as f:
            pickle.dump(data, f)
        os.chmod(STATISTICS_CONFIG_FILE, 0o664)
        logger.info(f"Configuracion guardada en {STATISTICS_CONFIG_FILE}: {data}")
    except Exception as e:
        logger.error(f"Error al guardar configuracion: {e}", exc_info=True)
        raise

def get_latest_excel_file():
    """Obtiene el archivo statistics_results_*.xlsx mas reciente."""
    try:
        os.makedirs(STATISTICS_OUTPUT_DIR, exist_ok=True)
        excel_files = glob.glob(os.path.join(STATISTICS_OUTPUT_DIR, "statistics_results_*.xlsx"))
        if not excel_files:
            logger.debug(f"No se encontraron archivos Excel en {STATISTICS_OUTPUT_DIR}")
            return None
        latest_file = max(excel_files, key=os.path.getctime)
        logger.info(f"Archivo Excel mas reciente: {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"Error al buscar archivo Excel: {e}", exc_info=True)
        return None

def load_results_from_excel():
    """Carga los resultados estadisticos desde el archivo Excel mas reciente."""
    try:
        latest_excel = get_latest_excel_file()
        if not latest_excel or not os.path.exists(latest_excel):
            logger.debug(f"No hay archivo Excel disponible: {latest_excel}")
            return {}
        df = pd.read_excel(latest_excel)
        results = {}
        for _, row in df.iterrows():
            variable = row['Variable']
            stats = {k: v for k, v in row.items() if k != 'Variable'}
            results[variable] = stats
        logger.info(f"Resultados cargados desde {latest_excel}")
        return results
    except Exception as e:
        logger.error(f"Error al cargar resultados: {e}", exc_info=True)
        return {}

def load_statistics_config():
    """Carga la configuracion de estadisticas desde un archivo pickle."""
    try:
        if os.path.exists(STATISTICS_CONFIG_FILE):
            with open(STATISTICS_CONFIG_FILE, 'rb') as f:
                data = pickle.load(f)
                logger.debug(f"Configuracion cargada: {data}")
                return data
        return {'processing': False, 'error': None, 'timestamp': None}
    except Exception as e:
        logger.error(f"Error al cargar configuracion: {e}", exc_info=True)
        return {'processing': False, 'error': None, 'timestamp': None}

def get_available_variables(main_folder):
    """Obtiene las variables disponibles verificando las carpetas de datos."""
    try:
        if not os.path.exists(main_folder):
            logger.error(f"Directorio no existe: {main_folder}")
            return []
        variables = []
        date_folders = [f for f in os.listdir(main_folder) if re.match(r'\d{4}-\d{2}-\d{2}', f)]
        if not date_folders:
            logger.error(f"No se encontraron carpetas de fechas en {main_folder}")
            return []
        for var in VARIABLES:
            var_lower = var.lower()
            for date_folder in date_folders:
                base_date_path = os.path.join(main_folder, date_folder)
                for folder in os.listdir(base_date_path):
                    if folder.lower() == var_lower:
                        var_folder = os.path.join(base_date_path, folder)
                        if not os.access(var_folder, os.R_OK):
                            logger.warning(f"Sin permisos de lectura: {var_folder}")
                            continue
                        txt_files = [f for f in os.listdir(var_folder) if f.endswith('.txt')]
                        if txt_files:
                            variables.append(var)
                            break
        variables = sorted(list(set(variables)))
        logger.info(f"Variables disponibles: {variables}")
        return variables
    except Exception as e:
        logger.error(f"Error al obtener variables: {e}", exc_info=True)
        return []
        

def check_data_availability(variables, start_date, end_date):
    """Verifica si existen datos para las variables y fechas especificadas."""
    try:
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        dates = pd.date_range(start=start_date_dt, end=end_date_dt, freq='D')
        variables_list = variables.split(',')
        found_data = False
        missing_vars = []
        for variable in variables_list:
            variable_lower = variable.lower()
            var_found = False
            for date in dates:
                date_str = date.strftime('%Y-%m-%d')
                base_date_path = os.path.join(BASE_DIR, date_str)
                if os.path.exists(base_date_path):
                    for folder in os.listdir(base_date_path):
                        if folder.lower() == variable_lower:
                            date_folder = os.path.join(base_date_path, folder)
                            txt_files = [f for f in os.listdir(date_folder) if f.endswith('.txt')]
                            if txt_files:
                                logger.debug(f"Datos encontrados para {variable} en {date_str}: {txt_files[:5]}")
                                var_found = True
                                found_data = True
                                break
                    if var_found:
                        break
            if not var_found:
                missing_vars.append(variable)
        if not found_data:
            error_msg = f"No se encontraron datos para {variables} en {start_date} a {end_date}. Variables sin datos: {missing_vars}. Directorio: {BASE_DIR}"
            logger.warning(error_msg)
            return False
        if missing_vars:
            logger.warning(f"Algunas variables sin datos: {missing_vars}")
        logger.info(f"Datos disponibles para al menos una variable en {variables}")
        return True
    except Exception as e:
        logger.error(f"Error al verificar datos: {e}", exc_info=True)
        return False

def main():
    """Funcion principal para la pagina de Estadisticas."""
    # Actualizar cada 10 segundos para reflejar resultados o errores
    st_autorefresh(interval=10000, key="refresh_estadisticas")

    # Estilos CSS
    st.markdown("""
    <style>
    .main-button > button {
        background-color: #222222 !important;
        color: white !important;
        border-radius: 5px;
        width: 200px !important;
        margin: 10px 5px !important;
        display: inline-block !important;
        padding: 5px 10px !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input,
    .stDateInput > div > div > input,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        background-color: #444444 !important;
        color: white !important;
        border-radius: 5px.
    }
    .stCheckbox > label {
        color: white !important;
    }
    .results-container {
        background-color: #2a2a2a;
        border: 2px solid #555;
        border-radius: 8px;
        padding: 15px;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("Estadisticas")

    # Verificar errores en la configuracion
    config = load_statistics_config()
    if config.get('error'):
        st.error(f"Error en el procesamiento anterior ({config.get('timestamp', 'desconocido')}): {config['error']}")
    if config.get('processing', False):
        st.info(f"Procesamiento en curso iniciado en {config.get('timestamp', 'desconocido')}. Espera a que finalice.")

    # Obtener variables disponibles
    variables = get_available_variables(BASE_DIR)
    if not variables:
        st.error("No se encontraron variables validas. Asegura que existan datos en /home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/.")
        return

    # Validar que las variables seleccionadas previamente sean validas
    if 'selected_variables' not in st.session_state:
        st.session_state.selected_variables = [variables[0]]
    else:
        st.session_state.selected_variables = [
            var for var in st.session_state.selected_variables if var in variables
        ]
        if not st.session_state.selected_variables:
            st.session_state.selected_variables = [variables[0]]

    # Seleccion de variables
    for i, var in enumerate(st.session_state.selected_variables):
        st.session_state.selected_variables[i] = st.selectbox(
            f"Selecciona variable {i + 1}",
            variables,
            index=variables.index(var) if var in variables else 0,
            format_func=lambda x: VARIABLES_DISPLAY.get(x, x),
            key=f"variable_{i}"
        )

    # Seleccion de rango de fechas
    today = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha de inicio", value=today - timedelta(days=7), max_value=today, key="start_date")
    with col2:
        end_date = st.date_input("Fecha de fin", value=today, max_value=today, key="end_date")

    # Diezmado opcional
    apply_decimation = st.checkbox("Aplicar diezmado", value=False, key="decimation")
    decimation_factor = 1
    if apply_decimation:
        decimation_factor = st.number_input("Factor de diezmado (entero > 1)", min_value=1, value=10, step=1, key="decimation_factor")

    # Botones
    col_btn1, col2, col3 = st.columns([2, 1, 1])
    with col_btn1:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Calcular Estadisticas"):
            if start_date > end_date:
                st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
                return
            variables_str = ",".join(st.session_state.selected_variables)
            if not check_data_availability(variables_str, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')):
                st.error(f"No hay datos disponibles para {variables_str} en el rango {start_date} a {end_date}. Verifica que existan archivos .txt en /home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/.")
                return
            with st.spinner("Calculando estadisticas, por favor espera..."):
                try:
                    # Guardar configuracion
                    save_statistics_config(variables_str, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), decimation_factor)
                    # Ejecutar procesar_estadisticas.py directamente
                    cmd = [
                        "/home/pi/Desktop/Medidor/venv/bin/python3",
                        "/home/pi/Desktop/Medidor/procesar_estadisticas.py",
                        variables_str,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        str(decimation_factor)
                    ]
                    logger.debug(f"Ejecutando comando: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=86400  # 24 horas para procesamientos largos
                    )
                    # Actualizar configuracion
                    config = load_statistics_config()
                    config['processing'] = False
                    config['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    if result.returncode == 0:
                        config['error'] = None
                        st.success("Estadisticas calculadas exitosamente. Mostrando resultados...")
                        logger.info(f"Procesamiento completado para {variables_str}. Salida: {result.stdout}")
                    else:
                        config['error'] = result.stderr.strip() or "Error desconocido. Revisa los logs en /home/pi/logs/procesar_estadisticas_error.log."
                        st.error(f"Error al calcular estadisticas: {config['error']}")
                        logger.error(f"Error en procesar_estadisticas.py: {config['error']}")
                    save_statistics_config(config)
                    # Forzar recarga de resultados
                    st.experimental_rerun()
                except subprocess.TimeoutExpired:
                    config = load_statistics_config()
                    config['processing'] = False
                    config['error'] = "Procesamiento excedio el tiempo maximo (24 horas)."
                    config['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_statistics_config(config)
                    st.error("Error: Tiempo de procesamiento excedido (24 horas).")
                    logger.error("Tiempo de espera excedido")
                except Exception as e:
                    config = load_statistics_config()
                    config['processing'] = False
                    config['error'] = f"Error: {str(e)}"
                    config['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_statistics_config(config)
                    st.error(f"Error al calcular estadisticas: {e}")
                    logger.error(f"Error al ejecutar procesar_estadisticas.py: {e}", exc_info=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Agregar Variable"):
            if len(st.session_state.selected_variables) < len(variables):
                st.session_state.selected_variables.append(variables[0])
            else:
                st.warning("No hay mas variables disponibles.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if len(st.session_state.selected_variables) > 1 and st.button("Eliminar Variable"):
            st.session_state.selected_variables.pop()
        st.markdown('</div>', unsafe_allow_html=True)

    # Mostrar resultados
    results = load_results_from_excel()
    if results:
        config = load_statistics_config()
        config_vars = config.get('variables', '').split(',')
        for variable in st.session_state.selected_variables:
            if variable in results:
                with st.container():
                    st.markdown('<div class="results-container">', unsafe_allow_html=True)
                    st.subheader(f"Estadisticas para {VARIABLES_DISPLAY.get(variable, variable)}")
                    st.table(results[variable])
                    if variable not in config_vars:
                        st.warning(f"Los resultados mostrados para {VARIABLES_DISPLAY.get(variable, variable)} son de un procesamiento anterior. Inicia un nuevo analisis para actualizar.")
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning(f"No se encontraron resultados para {VARIABLES_DISPLAY.get(variable, variable)}. Asegura que los datos existan y el procesamiento se haya completado. Revisa los logs en /home/pi/logs/ para mas detalles.")
    else:
        st.info("No hay resultados disponibles. Selecciona variables y fechas, luego presiona 'Calcular Estadisticas'.")

def run():
    """Punto de entrada para la pagina de Estadisticas."""
    main()

if __name__ == "__main__":
    run()
