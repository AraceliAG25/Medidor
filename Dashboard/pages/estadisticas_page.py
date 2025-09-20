# -*- coding: utf-8 -*-
"""
estadisticas_page.py
--------------------
Purpose: Streamlit page for the dashboard to select variables and dates,
trigger processing in a separate script, and display results from the latest Excel file.
Variables are obtained from data_collector.py.
"""

import streamlit as st
import pandas as pd
import os
import subprocess
import logging
import re
import glob
import time
from datetime import datetime, timedelta
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
    """Save the statistics configuration to a pickle file."""
    try:
        os.makedirs(os.path.dirname(STATISTICS_CONFIG_FILE), exist_ok=True)
        data = {
            'variables': variables,
            'start_date': start_date,
            'end_date': end_date,
            'decimation_factor': decimation_factor,
            'last_request_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'processing': True,
            'error': None,
            'request_id': str(time.time())  # Unique ID for each request
        }
        with open(STATISTICS_CONFIG_FILE, 'wb') as f:
            import pickle
            pickle.dump(data, f)
        os.chmod(STATISTICS_CONFIG_FILE, 0o664)
        logger.info(f"Statistics configuration saved to {STATISTICS_CONFIG_FILE}: {data}")
    except Exception as e:
        logger.error(f"Error saving statistics config to {STATISTICS_CONFIG_FILE}: {e}", exc_info=True)
        raise

def load_statistics_config():
    """Load the statistics configuration from a pickle file."""
    try:
        if os.path.exists(STATISTICS_CONFIG_FILE):
            with open(STATISTICS_CONFIG_FILE, 'rb') as f:
                import pickle
                data = pickle.load(f)
                logger.info(f"Statistics configuration loaded from {STATISTICS_CONFIG_FILE}: {data}")
                return data
        return {'processing': False, 'error': None, 'request_id': None}
    except Exception as e:
        logger.error(f"Error loading statistics config from {STATISTICS_CONFIG_FILE}: {e}", exc_info=True)
        return {'processing': False, 'error': None, 'request_id': None}

def get_latest_excel_file(request_id):
    """Get the most recent statistics_results_*.xlsx file."""
    try:
        os.makedirs(STATISTICS_OUTPUT_DIR, exist_ok=True)
        excel_files = glob.glob(os.path.join(STATISTICS_OUTPUT_DIR, "statistics_results_*.xlsx"))
        if not excel_files:
            logger.warning(f"No Excel files found in {STATISTICS_OUTPUT_DIR}")
            return None
        latest_file = max(excel_files, key=os.path.getctime)
        # Verify if the file is recent enough for the current request
        file_time = datetime.fromtimestamp(os.path.getctime(latest_file))
        request_time = datetime.now() if not request_id else datetime.fromtimestamp(float(request_id))
        if file_time < request_time - timedelta(minutes=5):
            logger.warning(f"Latest Excel file {latest_file} is too old for request_id {request_id}")
            return None
        logger.info(f"Latest Excel file found: {latest_file}")
        return latest_file
    except Exception as e:
        logger.error(f"Error finding latest Excel file: {e}", exc_info=True)
        return None

def get_available_variables(main_folder):
    """Get available variables from data_collector.py and verify folder existence."""
    try:
        if not os.path.exists(main_folder):
            logger.error(f"Base directory does not exist: {main_folder}")
            return []
        
        variables = []
        date_folders = [f for f in os.listdir(main_folder) if re.match(r'\d{4}-\d{2}-\d{2}', f)]
        logger.info(f"Date folders found in {main_folder}: {date_folders}")
        
        if not date_folders:
            logger.error(f"No date folders (YYYY-MM-DD) found in {main_folder}")
            return []
        
        for var in VARIABLES:
            var_lower = var.lower()
            found = False
            for date_folder in date_folders:
                base_date_path = os.path.join(main_folder, date_folder)
                for folder in os.listdir(base_date_path):
                    if folder.lower() == var_lower:
                        var_folder = os.path.join(base_date_path, folder)
                        if not os.access(var_folder, os.R_OK):
                            logger.warning(f"No read permissions for folder: {var_folder}")
                            continue
                        txt_files = [f for f in os.listdir(var_folder) if f.endswith('.txt')]
                        if txt_files:
                            variables.append(var)
                            logger.debug(f"Found valid variable: {var}, folder: {var_folder}, files: {txt_files}")
                            found = True
                            break
                if found:
                    break
            if not found:
                logger.warning(f"No data found for variable: {var} in any date folder")
        
        variables = sorted(list(set(variables)))
        if not variables:
            logger.error("No valid variables found in data folder")
        else:
            logger.info(f"Available variables: {variables}")
        return variables
    except Exception as e:
        logger.error(f"Error scanning variables: {e}", exc_info=True)
        return []

def load_results_from_excel(request_id):
    """Load statistical results from the latest Excel file."""
    try:
        latest_excel = get_latest_excel_file(request_id)
        if not latest_excel:
            logger.warning("No valid Excel file available to load results")
            return {}
        if os.path.exists(latest_excel):
            df = pd.read_excel(latest_excel)
            results = {}
            for _, row in df.iterrows():
                variable = row['Variable']
                stats = {k: v for k, v in row.items() if k != 'Variable'}
                results[variable] = stats
            logger.info(f"Loaded results from {latest_excel}")
            return results
        logger.warning(f"Excel file not found: {latest_excel}")
        return {}
    except Exception as e:
        logger.error(f"Error loading results from Excel: {e}", exc_info=True)
        return {}

def main():
    """Main function for the Estadisticas page."""
    # CSS styles consistent with medidor_dashboard.py
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
        border-radius: 5px;
    }
    .stCheckbox > label {
        color: white !important;
    }
    .centered-title {
        text-align: center;
        color: white;
        font-size: 24px;
        margin-bottom: 20px;
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

    # Get available variables
    variables = get_available_variables(BASE_DIR)
    if not variables:
        st.error("No se encontraron variables validas en la carpeta de datos. Asegurate de que existan datos en /home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/. Verifica que data_collector.py este ejecutandose y generando datos.")
        logger.error("No valid variables found in the data folder")
        return

    # Initialize session state
    if 'selected_variables' not in st.session_state:
        st.session_state.selected_variables = [variables[0] if variables else None]
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'last_request_id' not in st.session_state:
        st.session_state.last_request_id = None

    # Variable selection
    for i, var in enumerate(st.session_state.selected_variables):
        st.session_state.selected_variables[i] = st.selectbox(
            f"Selecciona una variable {i + 1}",
            variables,
            index=variables.index(var) if var in variables else 0,
            format_func=lambda x: VARIABLES_DISPLAY.get(x, x),
            key=f"variable_{i}"
        )

    # Date range selection
    today = datetime.now().date()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha de inicio", value=today - timedelta(days=7), max_value=today, key="start_date")
    with col2:
        end_date = st.date_input("Fecha de fin", value=today, max_value=today, key="end_date")

    # Optional decimation
    apply_decimation = st.checkbox("Aplicar diezmado", value=False, key="decimation")
    decimation_factor = 1
    if apply_decimation:
        decimation_factor = st.number_input("Factor de diezmado (entero > 1)", min_value=1, value=10, step=1, key="decimation_factor")

    # Buttons
    col_btn1, col2, col3 = st.columns([2, 1, 1])
    with col_btn1:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Calcular Estadisticas"):
            if start_date > end_date:
                st.error("La fecha de inicio no puede ser mayor que la fecha de fin.")
                logger.error("Start date is greater than end date")
                return
            with st.spinner("Iniciando procesamiento de estadisticas..."):
                logger.info("Calcular Estadisticas button pressed")
                try:
                    variables_str = ",".join(st.session_state.selected_variables)
                    save_statistics_config(variables_str, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), decimation_factor)
                    st.session_state.last_request_id = str(time.time())
                    st.session_state.processing = True
                    st.session_state.show_results = False
                    cmd = [
                        "/home/pi/Desktop/Medidor/venv/bin/python3",
                        "/home/pi/Desktop/Medidor/Dashboard/update_statistics_cron.py"
                    ]
                    logger.debug(f"Executing command in background: {' '.join(cmd)}")
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    st.success("Procesamiento de estadisticas iniciado. Los resultados se mostraran cuando esten listos.")
                except Exception as e:
                    st.error(f"Error al iniciar el procesamiento: {str(e)}")
                    logger.error(f"Error initiating update_statistics_cron.py: {str(e)}", exc_info=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Seleccionar Otra Variable"):
            if len(st.session_state.selected_variables) < len(variables):
                st.session_state.selected_variables.append(variables[0])
                st.session_state.show_results = False
                st.session_state.processing = False
                st.session_state.last_request_id = None
                logger.info("Added new variable selection")
            else:
                st.warning("No hay mas variables disponibles para seleccionar.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if len(st.session_state.selected_variables) > 1 and st.button("Remover Variable"):
            st.session_state.selected_variables.pop()
            st.session_state.show_results = False
            st.session_state.processing = False
            st.session_state.last_request_id = None
            logger.info("Removed last variable")
        st.markdown('</div>', unsafe_allow_html=True)

    # Check processing status and display results
    config = load_statistics_config()
    if config.get('processing', False):
        st.session_state.processing = True
    if config.get('error'):
        st.error(config['error'])
        logger.error(f"Stored error from config: {config['error']}")
    if st.session_state.processing:
        st.info("Procesando estadisticas... Por favor espera, los resultados se mostraran automaticamente.")
        results = load_results_from_excel(st.session_state.last_request_id)
        if results and config.get('request_id') == st.session_state.last_request_id:
            st.session_state.show_results = True
            st.session_state.processing = False
            config['processing'] = False
            config['error'] = None
            with open(STATISTICS_CONFIG_FILE, 'wb') as f:
                import pickle
                pickle.dump(config, f)
            os.chmod(STATISTICS_CONFIG_FILE, 0o664)
            logger.info("Processing completed, results found")
        else:
            logger.debug("Waiting for results Excel file")

    # Display results
    if st.session_state.show_results:
        results = load_results_from_excel(st.session_state.last_request_id)
        if results:
            for variable in st.session_state.selected_variables:
                if variable in results:
                    with st.container():
                        st.markdown('<div class="results-container">', unsafe_allow_html=True)
                        st.subheader(f"Estadisticas para {VARIABLES_DISPLAY.get(variable, variable)}")
                        st.table(results[variable])
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.warning(f"No se encontraron resultados para {VARIABLES_DISPLAY.get(variable, variable)}.")
        else:
            st.warning(f"No se encontraron resultados en el archivo Excel para la solicitud actual. Verifica que se hayan generado datos en {STATISTICS_OUTPUT_DIR}/statistics_results_*.xlsx.")

def run():
    """Entry point for the Estadisticas page."""
    main()

if __name__ == "__main__":
    run()
