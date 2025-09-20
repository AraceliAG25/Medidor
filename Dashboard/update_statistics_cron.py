# -*- coding: utf-8 -*-
"""
update_statistics_cron.py
--------------------
Purpose: Run procesar_estadisticas.py in the background when a statistics processing request is detected.
"""

import logging
import os
import subprocess
from datetime import datetime
import pickle
import pandas as pd
from config import BASE_DIR, LOG_DIR, STATISTICS_CONFIG_FILE, STATISTICS_OUTPUT_DIR

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'update_statistics_cron.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_statistics_config():
    """Load the statistics configuration from a pickle file."""
    try:
        if os.path.exists(STATISTICS_CONFIG_FILE):
            with open(STATISTICS_CONFIG_FILE, 'rb') as f:
                data = pickle.load(f)
                logger.info(f"Statistics configuration loaded from {STATISTICS_CONFIG_FILE}: {data}")
                return data
        return {'processing': False, 'error': None, 'request_id': None}
    except Exception as e:
        logger.error(f"Error loading statistics config from {STATISTICS_CONFIG_FILE}: {e}", exc_info=True)
        return {'processing': False, 'error': None, 'request_id': None}

def save_statistics_config(config):
    """Save the statistics configuration to a pickle file."""
    try:
        os.makedirs(os.path.dirname(STATISTICS_CONFIG_FILE), exist_ok=True)
        with open(STATISTICS_CONFIG_FILE, 'wb') as f:
            pickle.dump(config, f)
        os.chmod(STATISTICS_CONFIG_FILE, 0o664)
        logger.info(f"Statistics configuration saved to {STATISTICS_CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving statistics config to {STATISTICS_CONFIG_FILE}: {e}", exc_info=True)
        raise

def check_data_availability(variables, start_date, end_date):
    """Verify if data files exist for the given variables and date range."""
    try:
        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')
        dates = pd.date_range(start=start_date_dt, end=end_date_dt, freq='D')
        for variable in variables.split(','):
            variable_lower = variable.lower()
            for date in dates:
                date_str = date.strftime('%Y-%m-%d')
                base_date_path = os.path.join(BASE_DIR, date_str)
                if os.path.exists(base_date_path):
                    for folder in os.listdir(base_date_path):
                        if folder.lower() == variable_lower:
                            date_folder = os.path.join(base_date_path, folder)
                            txt_files = [f for f in os.listdir(date_folder) if f.endswith('.txt')]
                            if txt_files:
                                logger.info(f"Data found for {variable} on {date_str}: {txt_files[:5]}")
                                return True
                logger.debug(f"No data folder for {variable} on {date_str}")
        logger.warning(f"No data found for variables {variables} in range {start_date} to {end_date}")
        return False
    except Exception as e:
        logger.error(f"Error checking data availability: {e}", exc_info=True)
        return False

def update_statistics():
    """Run procesar_estadisticas.py if a processing request is pending."""
    try:
        logger.info("Checking for pending statistics processing request")
        config = load_statistics_config()
        if not config.get('processing', False):
            logger.info("No pending processing request")
            return
        
        variables = config.get('variables', '')
        start_date = config.get('start_date', '')
        end_date = config.get('end_date', '')
        decimation_factor = config.get('decimation_factor', 1)
        request_id = config.get('request_id', None)
        
        if not check_data_availability(variables, start_date, end_date):
            logger.error(f"No data available for {variables} in range {start_date} to {end_date}")
            config['processing'] = False
            config['error'] = (
                f"No se encontraron datos para {variables} en el rango {start_date} a {end_date}. "
                f"Asegurate de que existan archivos en /home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/."
            )
            save_statistics_config(config)
            return

        cmd = [
            "/home/pi/Desktop/Medidor/venv/bin/python3",
            "/home/pi/Desktop/Medidor/Dashboard/procesar_estadisticas.py",
            variables,
            start_date,
            end_date,
            str(decimation_factor)
        ]
        logger.debug(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1200  # Increased timeout for multiple variables
        )
        logger.debug(f"Subprocess result: returncode={result.returncode}, stdout={result.stdout}, stderr={result.stderr}")

        config['processing'] = False
        if result.returncode == 0:
            config['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            config['error'] = None
            logger.info(f"Statistics processing completed successfully for {variables}")
        else:
            config['error'] = result.stderr.strip() or (
                f"No se generaron resultados. Verifica los datos en "
                f"/home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/, "
                f"asegurate de que los archivos .txt tengan el formato 'YYYY-MM-DD HH:MM:SS,valor', "
                f"y revisa los logs en /home/pi/logs/procesar_estadisticas_error.log para detalles."
            )
            logger.error(f"Error in procesar_estadisticas.py: {config['error']}")
        save_statistics_config(config)

    except Exception as e:
        logger.error(f"Error in update_statistics: {e}", exc_info=True)
        config['processing'] = False
        config['error'] = f"Error processing statistics: {str(e)}"
        save_statistics_config(config)

if __name__ == "__main__":
    update_statistics()
