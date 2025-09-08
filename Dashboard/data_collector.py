from pymodbus.client.sync import ModbusSerialClient
import time
from datetime import datetime, timedelta
import pandas as pd
import os
import logging
import csv
import struct
import getpass
import pwd

VARIABLES = [
    'Corriente_linea1', 'Voltaje_fase_1', 'Potencia_activa_f1', 'Potencia_activa_Total',
    'Potencia_aparente_total', 'Factor_Potencia', 'frecuencia',
    'Energia_importada_activa_total', 'Energia_importada_reactiva_total', 'Factor_Potencia_Conversion'
]
UNITS = {
    'Corriente_linea1': 'A',
    'Voltaje_fase_1': 'V',
    'Potencia_activa_f1': 'kW',
    'Potencia_activa_Total': 'kW',
    'Potencia_aparente_total': 'kVA',
    'Factor_Potencia': '',
    'frecuencia': 'Hz',
    'Energia_importada_activa_total': 'kWh',
    'Energia_importada_reactiva_total': 'kVARh',
    'Factor_Potencia_Conversion': ''
}
VARIABLES_DISPLAY = {
    'Corriente_linea1': 'Corriente Linea 1',
    'Voltaje_fase_1': 'Voltaje Fase 1',
    'Potencia_activa_f1': 'Potencia Activa Fase 1',
    'Potencia_activa_Total': 'Potencia Activa Total',
    'Potencia_aparente_total': 'Potencia Aparente Total',
    'Factor_Potencia': 'Factor de Potencia',
    'frecuencia': 'Frecuencia',
    'Energia_importada_activa_total': 'Energia Importada Activa Total',
    'Energia_importada_reactiva_total': 'Energia Importada Reactiva Total',
    'Factor_Potencia_Conversion': 'Factor de Potencia Convertido'
}
BASE_DIRECTORY = "/home/pi/Desktop/Medidor/Rasp_Greco"
DATA_BUFFER_FILE = "/home/pi/Desktop/Medidor/Dashboard/data_buffer.csv"
PERSISTENT_BUFFER_FILE = "/home/pi/Desktop/Medidor/Dashboard/persistent_buffer.csv"
REGISTERS = {
    'Corriente_linea1': 2999,
    'Voltaje_fase_1': 3027,
    'Potencia_activa_f1': 3053,
    'Potencia_activa_Total': 3059,
    'Potencia_aparente_total': 3075,
    'Factor_Potencia': 3083,
    'frecuencia': 3109,
    'Energia_importada_activa_total': 45099,
    'Energia_importada_reactiva_total': 45103
}

os.makedirs("/home/pi/logs", exist_ok=True)
logging.basicConfig(
    filename="/home/pi/logs/data_collector_error.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def read_registers(client, address, unit=4):
    try:
        request = client.read_holding_registers(address, 2, unit=unit)
        if request.isError():
            raise ValueError(f"Error de lectura: {request}")
        variable = next((var for var, reg in REGISTERS.items() if reg == address), None)
        value = struct.unpack('>f', struct.pack('>HH', request.registers[0], request.registers[1]))[0]
        logger.debug(f"Lectura exitosa en {address} ({variable}): {value}")
        print(f"Lectura en {address} ({variable}): {value}")
        return value
    except Exception as e:
        logger.error(f"Error leyendo registros en {address}: {e}")
        print(f"Error en {address}: {e}")
        return None

def convert_factor_potencia(fpr):
    try:
        if 0 <= fpr <= 1:
            fpc = fpr
        elif -2 <= fpr <= -1:
            fpc = -2 - fpr
        elif -1 < fpr < 0:
            fpc = fpr
        elif 1 < fpr <= 2:
            fpc = 2 - fpr
        else:
            fpc = None
            logger.warning(f"Valor de Factor_Potencia fuera de rango: {fpr}")
            print(f"Valor de Factor_Potencia fuera de rango: {fpr}")
        logger.debug(f"Factor de Potencia convertido: fpr={fpr}, fpc={fpc}")
        print(f"Factor de Potencia convertido: fpr={fpr}, fpc={fpc}")
        return fpc
    except Exception as e:
        logger.error(f"Error convirtiendo Factor_Potencia: {e}")
        print(f"Error convirtiendo Factor_Potencia: {e}")
        return None

def get_file_path(variable, date, hour):
    date_str = date.strftime("%Y-%m-%d")
    hour_str = hour.strftime("%Y-%m-%d %H")
    directory = os.path.join(BASE_DIRECTORY, date_str, variable.lower())
    try:
        os.makedirs(directory, exist_ok=True)
        os.chmod(directory, 0o775)
        user = pwd.getpwnam(getpass.getuser())
        os.chown(directory, user.pw_uid, user.pw_gid)
        logger.debug(f"Ruta generada para {variable}: {directory}")
    except Exception as e:
        logger.error(f"Error creando directorio para {variable}: {e}")
        print(f"Error creando directorio para {variable}: {e}")
        raise
    file_path = os.path.join(directory, f"{hour_str}.txt")
    return file_path

def initialize_csv_buffer():
    try:
        os.makedirs(os.path.dirname(DATA_BUFFER_FILE), exist_ok=True)
        # Crear carpetas iniciales para todas las variables
        current_date = datetime.now().date()
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        for variable in VARIABLES:
            get_file_path(variable, current_date, current_hour)
        if not os.path.exists(DATA_BUFFER_FILE):
            with open(DATA_BUFFER_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp'] + VARIABLES)
            os.chmod(DATA_BUFFER_FILE, 0o664)
            user = pwd.getpwnam(getpass.getuser())
            os.chown(DATA_BUFFER_FILE, user.pw_uid, user.pw_gid)
            logger.info(f"Archivo {DATA_BUFFER_FILE} creado")
            print(f"Archivo {DATA_BUFFER_FILE} creado")
        if not os.path.exists(PERSISTENT_BUFFER_FILE):
            with open(PERSISTENT_BUFFER_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp'] + VARIABLES)
            os.chmod(PERSISTENT_BUFFER_FILE, 0o664)
            user = pwd.getpwnam(getpass.getuser())
            os.chown(PERSISTENT_BUFFER_FILE, user.pw_uid, user.pw_gid)
            logger.info(f"Archivo {PERSISTENT_BUFFER_FILE} creado")
            print(f"Archivo {PERSISTENT_BUFFER_FILE} creado")
    except Exception as e:
        logger.error(f"Error inicializando CSV o carpetas: {e}", exc_info=True)
        print(f"Error inicializando CSV o carpetas: {e}")
        raise

def save_to_csv_buffer(data, timestamp):
    try:
        temp_file = DATA_BUFFER_FILE + '.tmp'
        row = {'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        for var in VARIABLES:
            row[var] = data.get(var, None)
        logger.debug(f"Datos a guardar en CSV: {row}")
        print(f"Datos a guardar en CSV: {row}")
        df = pd.DataFrame([row], columns=['timestamp'] + VARIABLES)
        if os.path.exists(DATA_BUFFER_FILE):
            existing_df = pd.read_csv(DATA_BUFFER_FILE)
            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'], errors='coerce')
            one_month_ago = timestamp - timedelta(days=30)
            existing_df = existing_df[existing_df['timestamp'] >= one_month_ago].dropna(subset=['timestamp'])
            df = pd.concat([existing_df, df], ignore_index=True)
            logger.debug(f"Datos existentes en CSV: {len(existing_df)} filas")
            print(f"Datos existentes en CSV: {len(existing_df)} filas")
        else:
            logger.info(f"Creando nuevo archivo {DATA_BUFFER_FILE}")
            print(f"Creando nuevo archivo {DATA_BUFFER_FILE}")
        df.to_csv(temp_file, index=False)
        os.rename(temp_file, DATA_BUFFER_FILE)
        os.chmod(DATA_BUFFER_FILE, 0o664)
        user = pwd.getpwnam(getpass.getuser())
        os.chown(DATA_BUFFER_FILE, user.pw_uid, user.pw_gid)
        logger.info(f"Datos guardados en {DATA_BUFFER_FILE}: {row}")
        print(f"Datos guardados en {DATA_BUFFER_FILE}: {row}")
    except Exception as e:
        logger.error(f"Error guardando en {DATA_BUFFER_FILE}: {e}", exc_info=True)
        print(f"Error guardando en {DATA_BUFFER_FILE}: {e}")
        raise

def update_persistent_buffer():
    try:
        if os.path.exists(DATA_BUFFER_FILE):
            df = pd.read_csv(DATA_BUFFER_FILE)
            df.to_csv(PERSISTENT_BUFFER_FILE, index=False)
            os.chmod(PERSISTENT_BUFFER_FILE, 0o664)
            user = pwd.getpwnam(getpass.getuser())
            os.chown(PERSISTENT_BUFFER_FILE, user.pw_uid, user.pw_gid)
            logger.info(f"Buffer persistente actualizado en {PERSISTENT_BUFFER_FILE}")
            print(f"Buffer persistente actualizado en {PERSISTENT_BUFFER_FILE}")
    except Exception as e:
        logger.error(f"Error actualizando buffer persistente: {e}", exc_info=True)
        print(f"Error actualizando buffer persistente: {e}")

def connect_modbus():
    client = ModbusSerialClient(
        method="rtu",
        port="/dev/ttyUSB0",
        stopbits=1,
        bytesize=8,
        parity='E',
        baudrate=38400,
        timeout=3
    )
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            if client.connect():
                logger.info("Conexion Modbus establecida correctamente")
                return client
            else:
                logger.error(f"Intento de conexion {attempt + 1} fallido")
        except Exception as e:
            logger.error(f"Intento de conexion {attempt + 1} fallido: {e}")
        if attempt < max_attempts - 1:
            time.sleep(2)
    logger.error("No se pudo conectar al medidor despues de %d intentos", max_attempts)
    return None
    

def main():
    client = connect_modbus()
    if not client:
        logger.error("No se pudo conectar al medidor. Terminando programa.")
        print("No se pudo conectar al medidor. Terminando programa.")
        return
    initialize_csv_buffer()
    current_date = datetime.now().date()
    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    last_persistent_update = datetime.now()
    try:
        while True:
            timestamp = datetime.now()
            new_date = timestamp.date()
            new_hour = timestamp.replace(minute=0, second=0, microsecond=0)
            if new_date != current_date or new_hour != current_hour:
                current_date = new_date
                current_hour = new_hour
                logger.info(f"Nueva fecha/hora: {current_date}, {current_hour}")
                print(f"Nueva fecha/hora: {current_date}, {current_hour}")
            data = {'timestamp': timestamp}
            valid_data = True
            # Leer variables del medidor
            for variable, register in REGISTERS.items():
                value = read_registers(client, register)
                logger.debug(f"{variable}: {value}")
                print(f"{variable}: {value}")
                if value is not None:
                    data[variable] = value
                    file_path = get_file_path(variable, current_date, current_hour)
                    try:
                        with open(file_path, 'a', encoding='utf-8') as f:
                            f.write(f"{timestamp:%Y-%m-%d %H:%M:%S},{value}\n")
                            f.flush()
                            os.fsync(f.fileno())
                        os.chmod(file_path, 0o664)
                        user = pwd.getpwnam(getpass.getuser())
                        os.chown(file_path, user.pw_uid, user.pw_gid)
                        logger.debug(f"Datos escritos para {variable} en {file_path}: {timestamp}, {value}")
                        print(f"Datos escritos para {variable} en {file_path}: {timestamp}, {value}")
                    except Exception as e:
                        logger.error(f"Error escribiendo datos para {variable} en {file_path}: {e}")
                        print(f"Error escribiendo datos para {variable} en {file_path}: {e}")
                        valid_data = False
                else:
                    data[variable] = None
                    valid_data = False
                    logger.warning(f"No se pudo leer {variable} desde el registro {register}")
                    print(f"No se pudo leer {variable} desde el registro {register}")
            # Procesar Factor_Potencia_Conversion
            variable = 'Factor_Potencia_Conversion'
            file_path = get_file_path(variable, current_date, current_hour)
            fpc = convert_factor_potencia(data.get('Factor_Potencia')) if data.get('Factor_Potencia') is not None else None
            data[variable] = fpc
            try:
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f"{timestamp:%Y-%m-%d %H:%M:%S},{fpc if fpc is not None else 'None'}\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(file_path, 0o664)
                user = pwd.getpwnam(getpass.getuser())
                os.chown(file_path, user.pw_uid, user.pw_gid)
                logger.debug(f"Datos escritos para {variable} en {file_path}: {timestamp}, {fpc if fpc is not None else 'None'}")
                print(f"Datos escritos para {variable} en {file_path}: {timestamp}, {fpc if fpc is not None else 'None'}")
            except Exception as e:
                logger.error(f"Error escribiendo datos para {variable} en {file_path}: {e}")
                print(f"Error escribiendo datos para {variable} en {file_path}: {e}")
                valid_data = False
            if valid_data:
                save_to_csv_buffer(data, timestamp)
            else:
                logger.warning("No se guardaron datos en el buffer debido a valores no validos")
                print("No se guardaron datos en el buffer debido a valores no validos")
            if (timestamp - last_persistent_update).total_seconds() >= 300:
                update_persistent_buffer()
                last_persistent_update = timestamp
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Programa terminado por el usuario")
        print("Programa terminado por el usuario")
    except Exception as e:
        logger.error(f"Error en el bucle principal: {e}", exc_info=True)
        print(f"Error en el bucle principal: {e}")
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
