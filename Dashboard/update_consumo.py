import pandas as pd
from datetime import datetime, timedelta
import pickle
import os
import logging
import csv
from data_collector import VARIABLES, VARIABLES_DISPLAY, UNITS

logging.basicConfig(
    filename='/home/pi/logs/update_consumo_error.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONSUMO_CONFIG_FILE = "/home/pi/Desktop/Medidor/Dashboard/consumo_config.pkl"
CONSUMO_CSV_FILE = "/home/pi/Desktop/Medidor/Dashboard/consumo_metrics.csv"
BASE_DIR = "/home/pi/Desktop/Medidor/Rasp_Greco"

def limpiar_valor(valor):
    try:
        return float(valor)
    except (ValueError, TypeError):
        logger.warning(f"Valor no numerico: {valor}")
        return None

def read_single_txt_file(file_path):
    try:
        contenido = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) != 2:
                    continue
                fecha, valor = parts
                fecha = fecha.strip().split('.')[0]
                valor_limpio = limpiar_valor(valor)
                if valor_limpio is None:
                    continue
                fecha_dt = pd.to_datetime(fecha, format='%Y-%m-%d %H:%M:%S', errors='coerce')
                if pd.isna(fecha_dt):
                    continue
                contenido.append([fecha_dt, valor_limpio])
        if not contenido:
            logger.warning(f"No se encontraron datos validos en {file_path}")
            return pd.DataFrame(columns=['fecha', 'valor'])
        df = pd.DataFrame(contenido, columns=['fecha', 'valor'])
        df = df.sort_values('fecha').dropna().reset_index(drop=True)
        logger.info(f"Datos leidos de {file_path}: {len(df)} filas")
        return df
    except Exception as e:
        logger.error(f"Error leyendo archivo {file_path}: {e}")
        return pd.DataFrame(columns=['fecha', 'valor'])

def load_consumo_data():
    default_data = {
        'fecha_inicio': 'No disponible',
        'costo_kwh': 0.0,
        'energia_inicial': 0.0,
        'usar_valor_energia': False,
        'consumo': 0.0,
        'costo': 0.0,
        'dias_transcurridos': 0,
        'consumo_hoy': 0.0,
        'costo_hoy': 0.0,
        'demanda_maxima': 0.0,
        'estimacion_factura': 0.0,
        'fecha_fin': 'No disponible'
    }
    try:
        if os.path.exists(CONSUMO_CONFIG_FILE):
            with open(CONSUMO_CONFIG_FILE, 'rb') as f:
                data = pickle.load(f)
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                        logger.warning(f"Clave {key} no encontrada en {CONSUMO_CONFIG_FILE}, usando valor por defecto: {default_data[key]}")
                logger.info(f"Configuracion de consumo cargada desde {CONSUMO_CONFIG_FILE}")
                return data
    except Exception as e:
        logger.error(f"Error al cargar {CONSUMO_CONFIG_FILE}: {e}")
    return default_data

def save_consumo_data(fecha_inicio, costo_kwh, energia_inicial, usar_valor_energia, consumo, costo, dias_transcurridos, consumo_hoy, costo_hoy, demanda_maxima, estimacion_factura, fecha_fin):
    try:
        os.makedirs(os.path.dirname(CONSUMO_CONFIG_FILE), exist_ok=True)
        data = {
            'fecha_inicio': fecha_inicio,
            'costo_kwh': costo_kwh,
            'energia_inicial': energia_inicial,
            'usar_valor_energia': usar_valor_energia,
            'consumo': consumo,
            'costo': costo,
            'dias_transcurridos': dias_transcurridos,
            'consumo_hoy': consumo_hoy,
            'costo_hoy': costo_hoy,
            'demanda_maxima': demanda_maxima,
            'estimacion_factura': estimacion_factura,
            'fecha_fin': fecha_fin
        }
        with open(CONSUMO_CONFIG_FILE, 'wb') as f:
            pickle.dump(data, f)
        os.chmod(CONSUMO_CONFIG_FILE, 0o664)
        # Guardar en CSV
        csv_data = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'dias_transcurridos': dias_transcurridos,
            'consumo_hoy': consumo_hoy,
            'costo_hoy': costo_hoy,
            'demanda_maxima': demanda_maxima,
            'consumo_acumulado': consumo,
            'costo_acumulado': costo,
            'estimacion_factura': estimacion_factura
        }
        with open(CONSUMO_CSV_FILE, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data.keys())
            writer.writeheader()
            writer.writerow(csv_data)
        os.chmod(CONSUMO_CSV_FILE, 0o664)
        logger.info(f"Datos de consumo guardados en {CONSUMO_CONFIG_FILE} y {CONSUMO_CSV_FILE}")
        return data
    except Exception as e:
        logger.error(f"Error al guardar {CONSUMO_CONFIG_FILE} o {CONSUMO_CSV_FILE}: {e}")
        return None
        

def calcular_metricas(fecha_inicio, costo_kwh, energia_inicial, usar_valor_energia):
    try:
        today = datetime.now().date()
        fecha_inicio_dt = pd.to_datetime(fecha_inicio)
        fecha_fin_dt = fecha_inicio_dt + timedelta(days=60)
        days_elapsed = (today - fecha_inicio_dt.date()).days
        if days_elapsed < 0:
            days_elapsed = 0
        previous_hour = (datetime.now() - timedelta(hours=1)).replace(minute=59, second=59, microsecond=0)
        previous_hour_str = previous_hour.strftime('%Y-%m-%d %H')
        today_start = datetime.combine(today, datetime.min.time())
        today_start_str = today_start.strftime('%Y-%m-%d %H')
        energia_dir = os.path.join(BASE_DIR, today.strftime('%Y-%m-%d'), 'energia_importada_activa_total')
        consumo_hoy = 0.0
        logger.info(f"Buscando archivo de la hora anterior: {previous_hour_str}.txt en {energia_dir}")
        if os.path.exists(energia_dir):
            today_first_file = os.path.join(energia_dir, f"{today_start_str}.txt")
            previous_hour_file = os.path.join(energia_dir, f"{previous_hour_str}.txt")
            if os.path.exists(today_first_file):
                df_today_first = read_single_txt_file(today_first_file)
                if not df_today_first.empty:
                    first_value_today = df_today_first['valor'].iloc[0]
                    logger.info(f"Primer valor del dia ({today_start_str}.txt): {first_value_today}")
                    if os.path.exists(previous_hour_file):
                        df_previous_hour = read_single_txt_file(previous_hour_file)
                        if not df_previous_hour.empty:
                            last_value_previous_hour = df_previous_hour['valor'].iloc[-1]
                            consumo_hoy = last_value_previous_hour - first_value_today
                            logger.info(f"Ultimo valor de la hora anterior ({previous_hour_str}.txt): {last_value_previous_hour}")
                            if consumo_hoy < 0:
                                consumo_hoy = 0.0
                            logger.info(f"Consumo hoy calculado: {consumo_hoy:.2f} kWh")
                        else:
                            logger.warning(f"No hay datos en {previous_hour_file}")
                    else:
                        logger.warning(f"Archivo {previous_hour_file} no encontrado")
                else:
                    logger.warning(f"No hay datos en {today_first_file}")
            else:
                logger.warning(f"Archivo {today_first_file} no encontrado")
        else:
            logger.warning(f"Directorio {energia_dir} no encontrado")
        costo_hoy = consumo_hoy * costo_kwh
        demanda_maxima = 0.0
        for root, _, files in os.walk(BASE_DIR):
            if 'potencia_activa_total' not in root.lower():
                continue
            date_dir = os.path.basename(os.path.dirname(root))
            try:
                dir_date = datetime.strptime(date_dir, '%Y-%m-%d').date()
                if dir_date < fecha_inicio_dt.date():
                    continue
            except ValueError:
                continue
            for file in sorted(files):
                if not file.endswith('.txt'):
                    continue
                file_path = os.path.join(root, file)
                df = read_single_txt_file(file_path)
                if not df.empty:
                    max_value = df['valor'].max()
                    if not pd.isna(max_value) and max_value > demanda_maxima:
                        demanda_maxima = max_value
        consumo_acumulado = 0.0
        first_file = os.path.join(BASE_DIR, fecha_inicio_dt.strftime('%Y-%m-%d'), 'energia_importada_activa_total', f"{fecha_inicio_dt.strftime('%Y-%m-%d')} 00.txt")
        if usar_valor_energia:
            first_value = energia_inicial
            logger.info(f"Usando valor de energia inicial: {first_value}")
        else:
            first_value = None
            if os.path.exists(first_file):
                df_first = read_single_txt_file(first_file)
                if not df_first.empty:
                    first_value = df_first['valor'].iloc[0]
                    logger.info(f"Valor inicial desde {first_file}: {first_value}")
            else:
                logger.warning(f"Archivo inicial {first_file} no encontrado")
        if first_value is not None and os.path.exists(previous_hour_file):
            df_previous_hour = read_single_txt_file(previous_hour_file)
            if not df_previous_hour.empty:
                last_value_previous_hour = df_previous_hour['valor'].iloc[-1]
                consumo_acumulado = last_value_previous_hour - first_value
                if consumo_acumulado < 0:
                    consumo_acumulado = 0.0
                logger.info(f"Consumo acumulado calculado: {consumo_acumulado:.2f} kWh")
            else:
                logger.warning(f"No hay datos en {previous_hour_file} para consumo acumulado")
        else:
            logger.warning(f"No se pudo calcular consumo acumulado: first_value={first_value}, previous_hour_file_exists={os.path.exists(previous_hour_file)}")
        costo_acumulado = consumo_acumulado * costo_kwh
        estimacion_factura = (costo_acumulado / max(days_elapsed, 1)) * 60 if days_elapsed > 0 else costo_acumulado
        logger.info(f"Metricas calculadas: Consumo={consumo_acumulado:.2f} kWh, Costo=${costo_acumulado:.2f} MXN, Dias={days_elapsed}, "
                    f"Consumo hoy={consumo_hoy:.2f} kWh, Costo hoy=${costo_hoy:.2f} MXN, Demanda maxima={demanda_maxima:.2f} kW, "
                    f"Estimacion factura=${estimacion_factura:.2f} MXN")
        return consumo_acumulado, costo_acumulado, days_elapsed, consumo_hoy, costo_hoy, demanda_maxima, estimacion_factura, fecha_fin_dt.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error calculando metricas: {e}")
        return 0.0, 0.0, 0, 0.0, 0.0, 0.0, 0.0, (fecha_inicio_dt + timedelta(days=60)).strftime('%Y-%m-%d')

def main():
    global base_dir
    base_dir = BASE_DIR
    logger.info("Iniciando actualizacion de consumo")
    consumo_data = load_consumo_data()
    if consumo_data['fecha_inicio'] == 'No disponible':
        logger.warning("No hay configuracion de consumo definida")
        return
    fecha_inicio = consumo_data['fecha_inicio']
    costo_kwh = consumo_data['costo_kwh']
    energia_inicial = consumo_data['energia_inicial']
    usar_valor_energia = consumo_data['usar_valor_energia']
    consumo, costo, dias_transcurridos, consumo_hoy, costo_hoy, demanda_maxima, estimacion_factura, fecha_fin = calcular_metricas(
        fecha_inicio, costo_kwh, energia_inicial, usar_valor_energia
    )
    save_consumo_data(
        fecha_inicio, costo_kwh, energia_inicial, usar_valor_energia,
        consumo, costo, dias_transcurridos, consumo_hoy, costo_hoy, demanda_maxima, estimacion_factura, fecha_fin
    )
    logger.info("Actualizacion de consumo completada")

if __name__ == "__main__":
    main()
