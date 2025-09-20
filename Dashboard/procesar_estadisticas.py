# -*- coding: utf-8 -*-
"""
procesar_estadisticas.py
--------------------
Purpose: Process statistical data for selected variables and date range,
and save results to an Excel file with timestamp in the statistics_outputs folder.
"""

import pandas as pd
import os
import sys
import numpy as np
import re
import logging
from datetime import datetime
from data_collector import VARIABLES, UNITS
from config import BASE_DIR, LOG_DIR, STATISTICS_OUTPUT_DIR

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'procesar_estadisticas_error.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_value(value):
    """Remove non-printable characters and return cleaned value."""
    try:
        if value is None or str(value).strip().lower() in ['none', '', 'nan']:
            logger.warning(f"Value is None, empty, or 'nan': {value}")
            return None
        cleaned = re.sub(r'[^\x20-\x7E]', '', str(value)).strip()
        if not cleaned:
            logger.warning(f"Empty value after cleaning: {value}")
            return None
        value_float = float(cleaned)
        return value_float
    except (ValueError, TypeError) as e:
        logger.error(f"Error cleaning value {value}: {e}", exc_info=True)
        return None

def format_date(date):
    """Format date to match YYYY-MM-DD HH:MM:SS."""
    try:
        date = str(date).strip().split('.')[0]
        date_dt = pd.to_datetime(date, format='%Y-%m-%d %H:%M:%S', errors='raise')
        return date_dt
    except Exception as e:
        logger.error(f"Error formatting date: {date}, error: {e}", exc_info=True)
        return None

def convert_power_factor(fpr):
    """Convert recorded power factor to valid range."""
    try:
        if fpr is None:
            return None
        fpr = float(fpr)
        if -1 <= fpr <= 1:
            return fpr
        elif -2 <= fpr < -1:
            return -2 - fpr
        elif 1 < fpr <= 2:
            return 2 - fpr
        else:
            logger.warning(f"Power factor out of expected range: {fpr}")
            return fpr
    except (ValueError, TypeError):
        logger.error(f"Invalid power factor value: {fpr}", exc_info=True)
        return None

def read_text_files_by_variable(main_folder, variable, start_date, end_date):
    """Read text files for a variable within the specified date range."""
    try:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date).replace(hour=23, minute=59, second=59)
        dates = pd.date_range(start=start_date.floor('h'), end=end_date.floor('h'), freq='h')
        full_content = []
        files_checked = []
        invalid_lines = []
        sample_lines = []
        variable_lower = variable.lower()
        logger.debug(f"Reading files for variable {variable} ({variable_lower}) from {start_date} to {end_date}")

        files_found = False
        for date_hour in dates:
            date_day = date_hour.strftime('%Y-%m-%d')
            hour = date_hour.strftime('%H')
            date_folder = None
            base_date_path = os.path.join(main_folder, date_day)
            if os.path.exists(base_date_path):
                for folder in os.listdir(base_date_path):
                    if folder.lower() == variable_lower:
                        date_folder = os.path.join(base_date_path, folder)
                        break
            if not date_folder:
                logger.debug(f"No folder found for {variable_lower} on {date_day}")
                continue
            file_name = f"{date_day} {hour}.txt"
            file_path = os.path.join(date_folder, file_name)
            files_checked.append(file_path)

            if os.path.isfile(file_path):
                files_found = True
                if not os.access(file_path, os.R_OK):
                    logger.warning(f"No read permissions for file: {file_path}")
                    continue
                logger.debug(f"Reading file: {file_path}")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    if not lines:
                        logger.warning(f"Empty file: {file_path}")
                        continue
                    if len(sample_lines) < 5:
                        sample_lines.extend(lines[:5-len(sample_lines)])
                    for line in lines:
                        try:
                            parts = line.strip().split(',')
                            if len(parts) != 2:
                                logger.warning(f"Invalid line format in {file_path}: {line}")
                                invalid_lines.append(line.strip())
                                continue
                            date, value = parts
                            date_dt = format_date(date)
                            if not date_dt:
                                logger.warning(f"Invalid date in {file_path}: {line}")
                                invalid_lines.append(line.strip())
                                continue
                            if start_date <= date_dt <= end_date:
                                value_float = clean_value(value)
                                if value_float is None and variable not in ['Factor_Potencia', 'Factor_Potencia_Conversion']:
                                    logger.warning(f"Invalid value in {file_path}: {line}")
                                    invalid_lines.append(line.strip())
                                    continue
                                if variable in ['Factor_Potencia', 'Factor_Potencia_Conversion']:
                                    value_float = convert_power_factor(value_float)
                                if value_float is not None:
                                    full_content.append([date_dt, value_float])
                            else:
                                logger.debug(f"Line outside date range in {file_path}: {line}")
                        except Exception as e:
                            logger.warning(f"Error processing line in {file_path}: {line}, error: {e}")
                            invalid_lines.append(line.strip())
                            continue
            else:
                logger.debug(f"File not found: {file_path}")

        if not files_found:
            error_msg = (
                f"No files found for variable {variable} in range {start_date} to {end_date}. "
                f"Checked paths: {files_checked[:5]}"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if full_content:
            df = pd.DataFrame(full_content, columns=['date', 'value'])
            df = df.sort_values('date').dropna().reset_index(drop=True)
            if df.empty:
                error_msg = (
                    f"No valid data points for {variable} in range {start_date} to {end_date}. "
                    f"Sample lines: {sample_lines[:5]}. Invalid lines: {invalid_lines[:5]}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"Loaded {len(df)} data points for {variable} from {start_date} to {end_date}")
            return df
        error_msg = (
            f"No valid data found for {variable} in range {start_date} to {end_date}. "
            f"Sample lines: {sample_lines[:5]}. Invalid lines: {invalid_lines[:5]}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        logger.error(f"Error reading files for {variable}: {e}", exc_info=True)
        raise RuntimeError(f"Error reading files for {variable}: {e}")

def analyze_data(df, variable):
    """Analyze data and calculate statistics."""
    try:
        if df.empty:
            logger.error(f"Empty dataframe for {variable}")
            raise ValueError(f"Empty dataframe for {variable}")

        values = df['value'].dropna()
        if values.empty:
            logger.error(f"No valid values for {variable}")
            raise ValueError(f"No valid values for {variable}")

        maximum = values.max()
        minimum = values.min()
        average = values.mean()
        std_dev = values.std()
        median = values.median()
        percentile_25 = values.quantile(0.25)
        percentile_75 = values.quantile(0.75)

        change_rates = np.abs(values.diff().dropna()) / ((df['date'].diff().dropna().dt.total_seconds()) + 1e-10)
        avg_change_rate = change_rates.mean() if not change_rates.empty else 0
        relative_deviation = (std_dev / average * 100) if average != 0 else 0

        max_idx = values.idxmax()
        min_idx = values.idxmin()
        max_time = df.loc[max_idx, 'date'].strftime('%Y-%m-%d %H:%M:%S') if not pd.isna(max_idx) else ''
        min_time = df.loc[min_idx, 'date'].strftime('%Y-%m-%d %H:%M:%S') if not pd.isna(min_idx) else ''

        events_out_of_range = 0
        normal_time = 0
        abnormal_time = 0

        if variable in ['Corriente_linea1', 'Voltaje_fase_1', 'Factor_Potencia', 'frecuencia']:
            lower_limit = {'Corriente_linea1': 0, 'Voltaje_fase_1': 108, 'Factor_Potencia': 0.90, 'frecuencia': 59.9}
            upper_limit = {'Corriente_linea1': average * 1.2, 'Voltaje_fase_1': 132, 'Factor_Potencia': 1.10, 'frecuencia': 60.1}
            out_of_range_mask = (values < lower_limit.get(variable, -float('inf'))) | (values > upper_limit.get(variable, float('inf')))
            events_out_of_range = out_of_range_mask.sum()

            df['state'] = out_of_range_mask
            df['interval'] = df['date'].diff().dt.total_seconds().fillna(0)
            abnormal_time = df[df['state']]['interval'].sum()
            normal_time = df[~df['state']]['interval'].sum()

        difference = 0
        if variable == 'Energia_importada_activa_total':
            if len(values) >= 2:
                difference = values.iloc[-1] - values.iloc[0]
            results = {'Diferencia': f"{difference:.2f} {UNITS.get(variable, '')}"}
        else:
            results = {
                'Valor Maximo': f"{maximum:.2f} {UNITS.get(variable, '')}",
                'Fecha del Maximo': max_time,
                'Valor Minimo': f"{minimum:.2f} {UNITS.get(variable, '')}",
                'Fecha del Minimo': min_time,
                'Promedio': f"{average:.2f} {UNITS.get(variable, '')}",
                'Desviacion Estandar': f"{std_dev:.2f} {UNITS.get(variable, '')}",
                'Mediana': f"{median:.2f} {UNITS.get(variable, '')}",
                'Percentil 25': f"{percentile_25:.2f} {UNITS.get(variable, '')}",
                'Percentil 75': f"{percentile_75:.2f} {UNITS.get(variable, '')}",
                'Tasa de Cambio Promedio': f"{avg_change_rate:.4f} {UNITS.get(variable, '')}/s",
                'Desviacion Relativa (%)': f"{relative_deviation:.2f}%",
                'Eventos Fuera de Rango': events_out_of_range,
                'Tiempo Normal (s)': f"{normal_time:.2f}",
                'Tiempo Anormal (s)': f"{abnormal_time:.2f}"
            }

        logger.info(f"Statistics calculated for {variable}: {results}")
        return results
    except Exception as e:
        logger.error(f"Error analyzing data for {variable}: {e}", exc_info=True)
        raise RuntimeError(f"Error analyzing data for {variable}: {e}")

def main():
    """Process statistics for given variables and date range, and save to Excel with timestamp."""
    logger.info(f"Starting procesar_estadisticas.py with arguments: {sys.argv}")
    if len(sys.argv) != 5:
        logger.error(f"Expected 5 arguments, got {len(sys.argv)}: {sys.argv}")
        print(f"Error: Expected 5 arguments, got {len(sys.argv)}")
        sys.exit(1)

    try:
        variables = sys.argv[1].split(',')
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        decimation_factor = int(sys.argv[4])
        logger.info(f"Processing variables: {variables}, start_date: {start_date}, end_date: {end_date}, decimation_factor: {decimation_factor}")

        results_list = []
        for variable in variables:
            if variable not in VARIABLES:
                logger.warning(f"Variable {variable} not in VARIABLES list: {VARIABLES}")
                print(f"Warning: Variable {variable} not in VARIABLES list")
                continue
            try:
                df = read_text_files_by_variable(BASE_DIR, variable, start_date, end_date)
                if decimation_factor > 1:
                    df = df.iloc[::decimation_factor].reset_index(drop=True)
                results = analyze_data(df, variable)
                if results:
                    results['Variable'] = variable
                    results_list.append(results)
                    logger.info(f"Successfully processed variable: {variable}")
                else:
                    logger.warning(f"No results generated for {variable}")
                    print(f"Warning: No results generated for {variable}")
            except Exception as e:
                logger.error(f"Failed to process variable {variable}: {e}", exc_info=True)
                print(f"Error processing variable {variable}: {e}")
                continue

        if results_list:
            df_results = pd.DataFrame(results_list)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            results_excel = os.path.join(STATISTICS_OUTPUT_DIR, f"statistics_results_{timestamp}.xlsx")
            os.makedirs(STATISTICS_OUTPUT_DIR, exist_ok=True)
            df_results.to_excel(results_excel, index=False)
            os.chmod(results_excel, 0o664)
            logger.info(f"Results saved to {results_excel}")
        else:
            error_msg = (
                f"No se generaron resultados para ninguna variable. "
                f"Verifica los datos en /home/pi/Desktop/Medidor/Rasp_Greco/YYYY-MM-DD/variable/, "
                f"asegurate de que los archivos .txt tengan el formato 'YYYY-MM-DD HH:MM:SS,valor', "
                f"y revisa los logs en /home/pi/logs/procesar_estadisticas_error.log para detalles."
            )
            logger.error(error_msg)
            print(error_msg)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
