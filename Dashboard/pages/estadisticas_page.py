# -*- coding: utf-8 -*-
"""
estadisticas_page.py
--------------------
Purpose: Streamlit page for the dashboard that allows selecting multiple variables and dates,
triggers processing in a separate script, and displays results from an Excel file.
Variables are obtained from data_collector.py.
"""

import streamlit as st
import pandas as pd
import os
import subprocess
import logging
import re
from datetime import datetime, timedelta
from data_collector import VARIABLES, VARIABLES_DISPLAY

# Directory configurations
CARPETA_PRINCIPAL = "/home/pi/Desktop/Medidor/Rasp_Greco"
LOG_DIR = "/home/pi/logs"
RESULTS_EXCEL = "/home/pi/Desktop/Medidor/Dashboard/statistics_results.xlsx"

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'estadisticas_page_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
                var_folder = os.path.join(main_folder, date_folder, var_lower)
                if os.path.exists(var_folder):
                    if not os.access(var_folder, os.R_OK):
                        logger.warning(f"No read permissions for folder: {var_folder}")
                        continue
                    txt_files = [f for f in os.listdir(var_folder) if f.endswith('.txt')]
                    if txt_files:
                        variables.append(var)
                        logger.debug(f"Found valid variable: {var}, folder: {var_folder}, files: {txt_files}")
                        found = True
                        break
                    else:
                        logger.debug(f"No .txt files found in folder: {var_folder}")
                else:
                    logger.debug(f"Folder does not exist: {var_folder}")
            if not found:
                logger.warning(f"No data found for variable: {var} in any date folder")
        
        variables = sorted(list(set(variables)))  # Ensure no duplicates
        if not variables:
            logger.error("No valid variables found in data folder")
        else:
            logger.info(f"Available variables: {variables}")
        return variables
    except Exception as e:
        logger.error(f"Error scanning variables: {e}", exc_info=True)
        return []

def load_results_from_excel():
    """Load statistical results from Excel file."""
    try:
        if os.path.exists(RESULTS_EXCEL):
            df = pd.read_excel(RESULTS_EXCEL)
            results = {}
            for _, row in df.iterrows():
                variable = row['Variable']
                stats = {k: v for k, v in row.items() if k != 'Variable'}
                results[variable] = stats
            logger.info(f"Loaded results from {RESULTS_EXCEL}")
            return results
        logger.warning(f"Excel file not found: {RESULTS_EXCEL}")
        return {}
    except Exception as e:
        logger.error(f"Error loading results from {RESULTS_EXCEL}: {e}", exc_info=True)
        return {}
        

def main():
    """Main function for the Estadisticas page."""
    # CSS styles consistent with informacion_page.py
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
    variables = get_available_variables(CARPETA_PRINCIPAL)
    if not variables:
        st.error("No se encontraron variables válidas en la carpeta de datos.")
        logger.error("No valid variables found in the data folder")
        return

    # Initialize session state for selected variables
    if 'selected_variables' not in st.session_state:
        st.session_state.selected_variables = [variables[0] if variables else None]
    if 'show_results' not in st.session_state:
        st.session_state.show_results = False

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
        start_date = st.date_input("Fecha de inicio", value=today - timedelta(days=7), key="start_date")
    with col2:
        end_date = st.date_input("Fecha de fin", value=today, key="end_date")

    # Optional decimation
    apply_decimation = st.checkbox("Aplicar diezmado", value=False, key="decimation")
    decimation_factor = 1
    if apply_decimation:
        decimation_factor = st.number_input("Factor de diezmado (entero > 1)", min_value=1, value=10, step=1, key="decimation_factor")

    # Buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Calcular Estadísticas"):
            with st.spinner("Procesando datos..."):
                try:
                    # Prepare arguments for procesar_estadisticas.py
                    variables_str = ",".join(st.session_state.selected_variables)
                    cmd = [
                        "/home/pi/Desktop/Medidor/venv/bin/python3",
                        "/home/pi/Desktop/Medidor/Dashboard/procesar_estadisticas.py",
                        variables_str,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        str(decimation_factor)
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        st.session_state.show_results = True
                        logger.info(f"Successfully processed statistics for {variables_str}")
                    else:
                        st.error(f"Error al procesar estadísticas: {result.stderr}")
                        logger.error(f"Error in procesar_estadisticas.py: {result.stderr}")
                except Exception as e:
                    st.error(f"Error al ejecutar el procesamiento: {e}")
                    logger.error(f"Error executing procesar_estadisticas.py: {e}", exc_info=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_btn2:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if st.button("Seleccionar Otra Variable"):
            if len(st.session_state.selected_variables) < len(variables):
                st.session_state.selected_variables.append(variables[0])
                st.session_state.show_results = False
                logger.info("Added new variable selection")
            else:
                st.warning("No hay mas variables disponibles para seleccionar.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_btn3:
        st.markdown('<div class="main-button">', unsafe_allow_html=True)
        if len(st.session_state.selected_variables) > 1 and st.button("Remover Variable"):
            st.session_state.selected_variables.pop()
            st.session_state.show_results = False
            logger.info("Removed last variable")
        st.markdown('</div>', unsafe_allow_html=True)

    # Display results
    if st.session_state.show_results:
        results = load_results_from_excel()
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
            st.warning("No se encontraron resultados en el archivo Excel.")

def run():
    """Entry point for the Estadisticas page."""
    main()

if __name__ == "__main__":
    run()
