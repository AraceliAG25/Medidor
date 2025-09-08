import pandas as pd
import json
import os
import logging
from datetime import datetime
import getpass
import pwd
import time
import sys
import subprocess
import psutil

# Configuracion
VERIFICACION = 60  # Intervalo para alertas del sistema (segundos)
HEARTBEAT_INTERVAL = 5  # Intervalo para actualizar latido (segundos)
CPU_LIMITE = 60  # Umbral para uso de CPU (%)
MEMORIA_RAM_LIMITE = 90  # Umbral para uso de disco (%)
MEMORIA_LIBRE_LIMITE = 2  # Umbral para espacio libre (GB)
TEMPERATURA_LIMITE = 70  # Umbral para temperatura (C)
DISCO_LIBRE_INTERVAL = 3600  # Intervalo para verificar espacio libre en disco (1 hora en segundos)

# Variables electricas
VARIABLES = [
    'Corriente_linea1', 'Voltaje_fase_1', 'Potencia_activa_f1', 'Potencia_activa_Total',
    'Potencia_aparente_total', 'Factor_Potencia', 'frecuencia'
]
UNITS_PER_VARIABLE = {
    'Corriente_linea1': 'A',
    'Voltaje_fase_1': 'V',
    'Potencia_activa_f1': 'kW',
    'Potencia_activa_Total': 'kW',
    'Potencia_aparente_total': 'kVA',
    'Factor_Potencia': '',
    'frecuencia': 'Hz'
}
PER_VARIABLE_NAME = {
    'Corriente_linea1': 'Corriente Linea 1',
    'Voltaje_fase_1': 'Voltaje Fase 1',
    'Potencia_activa_f1': 'Potencia Activa Fase 1',
    'Potencia_activa_Total': 'Potencia Activa Total',
    'Potencia_aparente_total': 'Potencia Aparente Total',
    'Factor_Potencia': 'Factor de Potencia',
    'frecuencia': 'Frecuencia'
}
DATA_BUFFER_HOME = "/home/pi/Desktop/Medidor/Dashboard/data_buffer.csv"
ALERTS_CONFIG_HOME = "/home/pi/Desktop/Medidor/Dashboard/alerts_config.json"
ALERTS_STORAGE_HOME = "/home/pi/Desktop/Medidor/Dashboard/alerts_storage.json"
HEARTBEAT_FILE = "/home/pi/last_heartbeat.txt"
LOG_DIR = "/home/pi/logs"

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'alertas_manager_error.log'),
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_dependencies():
    required = ['pandas', 'psutil']
    for module in required:
        try:
            __import__(module)
        except ImportError:
            logger.error(f"Modulo {module} no esta instalado")
            print(f"Error: Modulo {module} no esta instalado. Instalalo con 'pip install {module}'")
            sys.exit(1)
    logger.debug("Todas las dependencias estan instaladas")

def initialize_alerts_config():
    default_config = {var: {"min": None, "max": None} for var in VARIABLES}
    try:
        os.makedirs(os.path.dirname(ALERTS_CONFIG_HOME), exist_ok=True)
        if not os.path.exists(ALERTS_CONFIG_HOME):
            with open(ALERTS_CONFIG_HOME, 'w') as f:
                json.dump(default_config, f, indent=4)
            os.chmod(ALERTS_CONFIG_HOME, 0o664)
            user = pwd.getpwnam(getpass.getuser())
            os.chown(ALERTS_CONFIG_HOME, user.pw_uid, user.pw_gid)
            logger.info(f"Archivo de configuracion creado: {ALERTS_CONFIG_HOME}")
            print(f"Archivo de configuracion creado: {ALERTS_CONFIG_HOME}")
        else:
            logger.debug(f"Archivo de configuracion ya existe: {ALERTS_CONFIG_HOME}")
    except Exception as e:
        logger.error(f"Error inicializando configuracion: {e}", exc_info=True)
        print(f"Error inicializando configuracion: {e}")
        sys.exit(1)

def initialize_alerts_storage():
    try:
        os.makedirs(os.path.dirname(ALERTS_STORAGE_HOME), exist_ok=True)
        if not os.path.exists(ALERTS_STORAGE_HOME):
            with open(ALERTS_STORAGE_HOME, 'w') as f:
                json.dump([], f, indent=4)
            os.chmod(ALERTS_STORAGE_HOME, 0o664)
            user = pwd.getpwnam(getpass.getuser())
            os.chown(ALERTS_STORAGE_HOME, user.pw_uid, user.pw_gid)
            logger.info(f"Archivo de almacenamiento creado: {ALERTS_STORAGE_HOME}")
            print(f"Archivo de almacenamiento creado: {ALERTS_STORAGE_HOME}")
        else:
            logger.debug(f"Archivo de almacenamiento ya existe: {ALERTS_STORAGE_HOME}")
    except Exception as e:
        logger.error(f"Error inicializando almacenamiento: {e}", exc_info=True)
        print(f"Error inicializando almacenamiento: {e}")
        sys.exit(1)

def load_alerts_config():
    try:
        with open(ALERTS_CONFIG_HOME, 'r') as f:
            config = json.load(f)
        logger.debug(f"Configuracion cargada: {config}")
        for var in VARIABLES:
            if var not in config:
                config[var] = {"min": None, "max": None}
        return config
    except Exception as e:
        logger.error(f"Error cargando configuracion: {e}", exc_info=True)
        print(f"Error cargando configuracion: {e}")
        return {var: {"min": None, "max": None} for var in VARIABLES}

def load_alerts_storage():
    try:
        with open(ALERTS_STORAGE_HOME, 'r') as f:
            alerts = json.load(f)
        logger.debug(f"Alertas cargadas: {len(alerts)} alertas")
        return alerts
    except Exception as e:
        logger.error(f"Error cargando almacenamiento: {e}", exc_info=True)
        print(f"Error cargando almacenamiento: {e}")
        return []

def save_alerts_storage(alerts):
    try:
        temp_file = ALERTS_STORAGE_HOME + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(alerts, f, indent=4)
        os.replace(temp_file, ALERTS_STORAGE_HOME)
        os.chmod(ALERTS_STORAGE_HOME, 0o664)
        user = pwd.getpwnam(getpass.getuser())
        os.chown(ALERTS_STORAGE_HOME, user.pw_uid, user.pw_gid)
        logger.debug(f"Alertas guardadas: {len(alerts)} alertas")
        print(f"Alertas guardadas en {ALERTS_STORAGE_HOME}")
    except Exception as e:
        logger.error(f"Error guardando alertas: {e}", exc_info=True)
        print(f"Error guardando alertas: {e}")

def update_heartbeat():
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(current_time)
        logger.debug(f"Latido actualizado: {current_time}")
    except Exception as e:
        logger.error(f"Error actualizando {HEARTBEAT_FILE}: {e}", exc_info=True)
        print(f"Error actualizando latido: {e}")

def check_raspberry_status():
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            logger.warning(f"No existe {HEARTBEAT_FILE}")
            return False
        with open(HEARTBEAT_FILE, 'r') as f:
            last_heartbeat = f.read().strip()
        last_heartbeat_time = datetime.strptime(last_heartbeat, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        time_diff = (current_time - last_heartbeat_time).total_seconds()
        if time_diff > HEARTBEAT_INTERVAL * 2:  # Tolerancia de 2 intervalos (10 segundos)
            logger.warning(f"Raspberry Pi inactiva: ultimo latido hace {time_diff:.2f} segundos")
            return False
        logger.debug("Raspberry Pi activa")
        return True
    except Exception as e:
        logger.error(f"Error verificando estado de Raspberry Pi: {e}", exc_info=True)
        return False

def get_cpu_usage():
    try:
        usage = psutil.cpu_percent(interval=1)
        logger.debug(f"Uso de CPU: {usage}%")
        return usage
    except Exception as e:
        logger.error(f"Error obteniendo uso de CPU: {e}", exc_info=True)
        print(f"Error obteniendo uso de CPU: {e}")
        return None

def get_disk_usage():
    try:
        usage = psutil.disk_usage('/')
        percent = usage.percent
        free_gb = usage.free / (1024**3)
        logger.debug(f"Uso de disco: {percent}%, Espacio libre: {free_gb:.2f} GB")
        return percent, free_gb
    except Exception as e:
        logger.error(f"Error obteniendo uso de disco: {e}", exc_info=True)
        print(f"Error obteniendo uso de disco: {e}")
        return None, None

def get_temperature():
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, check=True)
        temp_str = result.stdout.strip()
        temp = float(temp_str.split('=')[1].replace("'C", ""))
        logger.debug(f"Temperatura: {temp} C")
        return temp
    except Exception as e:
        logger.error(f"Error al obtener la temperatura: {e}", exc_info=True)
        print(f"Error al obtener la temperatura: {e}")
        return None

def check_internet():
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], capture_output=True, text=True, timeout=5)
        connected = result.returncode == 0
        logger.debug(f"Internet conectado: {connected}")
        return connected
    except Exception as e:
        logger.error(f"Error verificando Internet: {e}", exc_info=True)
        print(f"Error verificando Internet: {e}")
        return False
        

def UPDATE_alerts():
    try:
        current_time = datetime.now()
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        alerts = load_alerts_storage()
        
        # Inicializar alertas activas
        active_alerts = {var: None for var in VARIABLES + ['CPU', 'Disco_Uso', 'Disco_Libre', 'Temperatura', 'Internet', 'Sistema']}
        for alert in alerts:
            if not alert.get('end_time') and alert['variable'] in active_alerts:
                active_alerts[alert['variable']] = alert

        # Verificar estado de Raspberry Pi
        if not check_raspberry_status() and not active_alerts["Sistema"]:
            alert = {
                "variable": "Sistema",
                "start_time": timestamp,
                "end_time": None,
                "message": "Raspberry Pi inactiva",
                "value": None
            }
            alerts.insert(0, alert)
            active_alerts["Sistema"] = alert
            logger.info(f"Nueva alerta generada: {alert['message']}")
            print(f"Nueva alerta generada: {alert['message']}")
        elif check_raspberry_status() and active_alerts["Sistema"]:
            active_alerts["Sistema"]["end_time"] = timestamp
            active_alerts["Sistema"]["message"] = "Raspberry Pi inactiva"
            logger.info(f"Alerta finalizada: {active_alerts['Sistema']['message']}")
            print(f"Alerta finalizada: {active_alerts['Sistema']['message']}")
            active_alerts["Sistema"] = None

        # Monitoreo de variables electricas
        if os.path.exists(DATA_BUFFER_HOME):
            if not os.access(DATA_BUFFER_HOME, os.R_OK):
                logger.error(f"No hay permisos de lectura para {DATA_BUFFER_HOME}")
                print(f"Error: No hay permisos de lectura para {DATA_BUFFER_HOME}")
                return
            try:
                df = pd.read_csv(DATA_BUFFER_HOME, dtype_backend='numpy_nullable')
                logger.debug(f"Datos leidos: {len(df)} filas, columnas: {list(df.columns)}")
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                df = df.dropna(subset=['timestamp'])
                if df.empty:
                    logger.warning("No hay datos validos en data_buffer.csv")
                else:
                    latest_data = df.iloc[-1]
                    timestamp_electric = latest_data['timestamp']
                    config = load_alerts_config()
                    
                    for variable in VARIABLES:
                        if variable not in latest_data or pd.isna(latest_data[variable]):
                            logger.debug(f"No hay datos validos para {variable}")
                            continue
                        try:
                            value = float(latest_data[variable])
                        except (ValueError, TypeError) as e:
                            logger.error(f"Error convirtiendo {variable} a float: {latest_data[variable]}, error: {e}")
                            continue
                        min_val = config.get(variable, {}).get('min')
                        max_val = config.get(variable, {}).get('max')
                        logger.debug(f"Verificando {variable}: valor={value}, min={min_val}, max={max_val}")
                        if min_val is None or max_val is None:
                            logger.debug(f"No hay rangos definidos para {variable}")
                            continue
                        if value < min_val or value > max_val:
                            if not active_alerts[variable]:
                                alert = {
                                    'variable': variable,
                                    'start_time': timestamp_electric.strftime("%Y-%m-%d %H:%M:%S"),
                                    'end_time': None,
                                    'message': f"Valor de la {PER_VARIABLE_NAME[variable]} fuera de rango",
                                    'value': value
                                }
                                alerts.insert(0, alert)
                                active_alerts[variable] = alert
                                logger.info(f"Nueva alerta generada: {alert['message']}")
                                print(f"Nueva alerta generada: {alert['message']}")
                            else:
                                active_alerts[variable]['value'] = value
                                active_alerts[variable]['message'] = f"Valor de la {PER_VARIABLE_NAME[variable]} fuera de rango"
                                logger.debug(f"Alerta activa actualizada para {variable}: {active_alerts[variable]['message']}")
                        else:
                            if active_alerts[variable]:
                                active_alerts[variable]['end_time'] = timestamp_electric.strftime("%Y-%m-%d %H:%M:%S")
                                active_alerts[variable]['message'] = f"Valor de la {PER_VARIABLE_NAME[variable]} fuera de rango"
                                logger.info(f"Alerta finalizada: {active_alerts[variable]['message']}")
                                print(f"Alerta finalizada: {active_alerts[variable]['message']}")
                                active_alerts[variable] = None
            except pd.errors.EmptyDataError:
                logger.warning("data_buffer.csv esta vacio")
            except pd.errors.ParserError as e:
                logger.error(f"Error parseando data_buffer.csv: {e}", exc_info=True)
                print(f"Error parseando data_buffer.csv: {e}")
            except Exception as e:
                logger.error(f"Error procesando datos electricos: {e}", exc_info=True)
                print(f"Error procesando datos electricos: {e}")

        # Monitoreo del sistema
        global last_check_time, internet_disconnected_time, last_disk_free_check
        if last_check_time is None or (current_time - last_check_time).total_seconds() >= VERIFICACION:
            logger.debug("Ejecutando monitoreo del sistema")
            # Internet
            internet_connected = check_internet()
            if not internet_connected:
                if internet_disconnected_time is None:
                    internet_disconnected_time = current_time
            else:
                if internet_disconnected_time is not None and not active_alerts["Internet"]:
                    alert = {
                        "variable": "Internet",
                        "start_time": internet_disconnected_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "end_time": timestamp,
                        "message": "Conexion a Internet restablecida",
                        "value": None
                    }
                    alerts.insert(0, alert)
                    active_alerts["Internet"] = None
                    logger.info(f"Alerta finalizada: {alert['message']}")
                    print(f"Alerta finalizada: {alert['message']}")
                    internet_disconnected_time = None

            # CPU
            uso_cpu = get_cpu_usage()
            if uso_cpu is not None:
                if uso_cpu > CPU_LIMITE and not active_alerts["CPU"]:
                    alert = {
                        "variable": "CPU",
                        "start_time": timestamp,
                        "end_time": None,
                        "message": "Uso elevado del CPU",
                        "value": uso_cpu
                    }
                    alerts.insert(0, alert)
                    active_alerts["CPU"] = alert
                    logger.info(f"Nueva alerta generada: {alert['message']}")
                    print(f"Nueva alerta generada: {alert['message']}")
                elif uso_cpu <= CPU_LIMITE and active_alerts["CPU"]:
                    active_alerts["CPU"]["end_time"] = timestamp
                    active_alerts["CPU"]["message"] = "Uso elevado del CPU"
                    logger.info(f"Alerta finalizada: {active_alerts['CPU']['message']}")
                    print(f"Alerta finalizada: {active_alerts['CPU']['message']}")
                    active_alerts["CPU"] = None

            # Disco
            porcentaje_uso, espacio_libre = get_disk_usage()
            if porcentaje_uso is not None:
                if porcentaje_uso > MEMORIA_RAM_LIMITE and not active_alerts["Disco_Uso"]:
                    alert = {
                        "variable": "Disco_Uso",
                        "start_time": timestamp,
                        "end_time": None,
                        "message": f"Alerta: Uso de disco elevado ({porcentaje_uso:.2f}%)",
                        "value": porcentaje_uso
                    }
                    alerts.insert(0, alert)
                    active_alerts["Disco_Uso"] = alert
                    logger.info(f"Nueva alerta generada: {alert['message']}")
                    print(f"Nueva alerta generada: {alert['message']}")
                elif porcentaje_uso <= MEMORIA_RAM_LIMITE and active_alerts["Disco_Uso"]:
                    active_alerts["Disco_Uso"]["end_time"] = timestamp
                    active_alerts["Disco_Uso"]["message"] = f"Alerta finalizada: Uso de disco ({porcentaje_uso:.2f}%)"
                    logger.info(f"Alerta finalizada: {active_alerts['Disco_Uso']['message']}")
                    print(f"Alerta finalizada: {active_alerts['Disco_Uso']['message']}")
                    active_alerts["Disco_Uso"] = None

            if espacio_libre is not None:
                # Verificar espacio libre solo cada hora
                if last_disk_free_check is None or (current_time - last_disk_free_check).total_seconds() >= DISCO_LIBRE_INTERVAL:
                    if espacio_libre < MEMORIA_LIBRE_LIMITE and not active_alerts["Disco_Libre"]:
                        alert = {
                            "variable": "Disco_Libre",
                            "start_time": timestamp,
                            "end_time": None,
                            "message": f"Alerta: Espacio libre en disco bajo ({espacio_libre:.2f} GB)",
                            "value": espacio_libre
                        }
                        alerts.insert(0, alert)
                        active_alerts["Disco_Libre"] = alert
                        logger.info(f"Nueva alerta generada: {alert['message']}")
                        print(f"Nueva alerta generada: {alert['message']}")
                    elif espacio_libre >= MEMORIA_LIBRE_LIMITE and active_alerts["Disco_Libre"]:
                        active_alerts["Disco_Libre"]["end_time"] = timestamp
                        active_alerts["Disco_Libre"]["message"] = f"Alerta finalizada: Espacio libre en disco ({espacio_libre:.2f} GB)"
                        logger.info(f"Alerta finalizada: {active_alerts['Disco_Libre']['message']}")
                        print(f"Alerta finalizada: {active_alerts['Disco_Libre']['message']}")
                        active_alerts["Disco_Libre"] = None
                    last_disk_free_check = current_time

            # Temperatura
            temperatura = get_temperature()
            if temperatura is not None:
                if temperatura > TEMPERATURA_LIMITE and not active_alerts["Temperatura"]:
                    alert = {
                        "variable": "Temperatura",
                        "start_time": timestamp,
                        "end_time": None,
                        "message": f"Alerta: Temperatura elevada ({temperatura:.2f} C)",
                        "value": temperatura
                    }
                    alerts.insert(0, alert)
                    active_alerts["Temperatura"] = alert
                    logger.info(f"Nueva alerta generada: {alert['message']}")
                    print(f"Nueva alerta generada: {alert['message']}")
                elif temperatura <= TEMPERATURA_LIMITE and active_alerts["Temperatura"]:
                    active_alerts["Temperatura"]["end_time"] = timestamp
                    active_alerts["Temperatura"]["message"] = f"Alerta finalizada: Temperatura ({temperatura:.2f} C)"
                    logger.info(f"Alerta finalizada: {active_alerts['Temperatura']['message']}")
                    print(f"Alerta finalizada: {active_alerts['Temperatura']['message']}")
                    active_alerts["Temperatura"] = None

            last_check_time = current_time
            logger.debug("Monitoreo del sistema completado")

        save_alerts_storage(alerts)
    except Exception as e:
        logger.error(f"Error en UPDATE_alerts: {e}", exc_info=True)
        print(f"Error en UPDATE_alerts: {e}")

def main():
    check_dependencies()
    initialize_alerts_config()
    initialize_alerts_storage()
    global last_check_time, last_heartbeat_time, internet_disconnected_time, last_disk_free_check
    last_check_time = None
    last_heartbeat_time = None
    internet_disconnected_time = None
    last_disk_free_check = None
    last_checked = None
    try:
        while True:
            current_time = datetime.now()
            UPDATE_alerts()
            if os.path.exists(DATA_BUFFER_HOME):
                current_mtime = os.path.getmtime(DATA_BUFFER_HOME)
                if last_checked is None or current_mtime > last_checked:
                    logger.debug(f"Detectado cambio en {DATA_BUFFER_HOME}, procesando...")
                    last_checked = current_mtime
                else:
                    logger.debug(f"No hay cambios en {DATA_BUFFER_HOME}")
            else:
                logger.warning(f"No existe {DATA_BUFFER_HOME}")
            if last_heartbeat_time is None or (current_time - last_heartbeat_time).total_seconds() >= HEARTBEAT_INTERVAL:
                update_heartbeat()
                last_heartbeat_time = current_time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Programa terminado por el usuario")
        print("Programa terminado por el usuario")
    except Exception as e:
        logger.error(f"Error en el bucle principal: {e}", exc_info=True)
        print(f"Error en el bucle principal: {e}")

if __name__ == "__main__":
    main()
