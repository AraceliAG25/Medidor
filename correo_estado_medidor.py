import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import time
import datetime as dt
import psutil
import subprocess
import os



#tiempo entre cada verificacion en segundos
verificacion=60


#limites de dagtos criticos
cpu=60
memoria_ram=90
memoria=2
temperatura_raspberry=70


# Configuracion del correo
sender_address = "solucionesenergiainnovacion@gmail.com"
sender_password = "psvx asnh vluc rglh"
sender_server = 'smtp.gmail.com'
sender_port = 587
recipient_address = "solucionesenergiainnovacion@gmail.com"



tiempo_inicio = dt.datetime.now()
formatted_now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print("Fecha y hora actual: ", formatted_now)


def send_email(subject, body):
    """Envia un correo electronico con el estado del medidor o del sistema."""
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_address
        msg['To'] = recipient_address
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))


        with smtplib.SMTP(sender_server, sender_port) as server:
            server.starttls()
            server.login(sender_address, sender_password)
            server.sendmail(sender_address, recipient_address, msg.as_string())


        print("Correo enviado con Exito.")
    except Exception as e:
        print(f"Fallo al enviar el correo. Error: {e}")


def calculate_downtime(log_file):
    """Calcula y devuelve el tiempo de inactividad basado en el archivo de registro."""
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        boot_times = [dt.datetime.strptime(line.strip().split('Started: ')[1], '%Y-%m-%d %H:%M:%S') for line in lines if 'Started:' in line]


        if len(boot_times) < 2:
            print("No hay suficientes datos para calcular el tiempo de inactividad.")
            return None, None


        last_boot_time = boot_times[-1]
        downtime = (dt.datetime.now() - last_boot_time).total_seconds()

        

        dias = int(downtime//(24*3600))
        horas2 = int(downtime // 3600)
        #horas = int((downtime % (24*3600))// 3600)
        minutos = int((downtime % 3600) // 60)
        segundos = int(downtime % 60)


        fin = f"Tiempo de inactividad: {dias} dias {horas2} horas {minutos} minutos y {segundos} segundos"
        print("origin ",fin)
        return last_boot_time, fin


    except FileNotFoundError:
        print(f"El archivo {log_file} no se encuentra.")
        return None, None


def get_cpu_usage():
    """Obtiene el uso de CPU en porcentaje."""
    return psutil.cpu_percent(interval=1)

def get_disk_usage():
    """Obtiene el uso del disco."""
    usage = psutil.disk_usage('/')
    return usage.percent, usage.free, usage.total

def get_temperature():
    """Ejecuta el comando vcgencmd para obtener la temperatura de la CPU."""
    try:
        result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
        temp_str = result.stdout.strip()
        temp = float(temp_str.split('=')[1].replace("'C", ""))
        return temp
    except Exception as e:
        print(f"Error al obtener la temperatura: {e}")
        return None

def check_internet():
    """Verifica si hay conexion a Internet haciendo ping a Google DNS."""
    try:
        # Intentar hacer ping a Google DNS
        response = os.system("ping -c 1 8.8.8.8 > /dev/null 2>&1")
        return response == 0
    except Exception as e:
        print(f"Error al hacer ping: {e}")
        return False

def main():
    global log_file
    log_file = '/var/log/boot_time.log'

    # Inicializar el cliente RTU
    client = ModbusClient(method="rtu", port="/dev/ttyUSB0", stopbits=1, bytesize=8, parity='E', baudrate=38400)

    connection = client.connect()
    print(connection)
    print("Method:", client.method)
    print("Port:", client.port)
    print("Stopbits:", client.stopbits)
    print("Bytesize:", client.bytesize)
    print("Parity:", client.parity)
    print("Baudrate:", client.baudrate)

    last_status = None
    last_email_time = None  # Para hacer un seguimiento del Ultimo correo electronico enviado
    internet_disconnected_time = None  # Para registrar cuando se desconecto de Internet


    while True:
        # Intentar conectar al servidor Modbus
        connection = client.connect()
        estado_de_comunicacion = "Conexion establecida" if connection else "Error de conexion"

        # Verificar la conexion a Internet
        internet_connected = check_internet()

        # Verificar si el estado de comunicacion ha cambiado
        if estado_de_comunicacion != last_status:
            last_boot_time, fin = calculate_downtime(log_file)


            if last_boot_time and fin:
                subject = ' Oficina_Greco-Estado del medidor'#-----------------------------------------------------------
                body = (f"Fecha y hora actual: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Estado del medidor: {estado_de_comunicacion}\n"
                        f"method: {client.method}\n"
                        f"port: {client.port}\n"
                        f"stopbits: {client.stopbits}\n"
                        f"bytesize: {client.bytesize}\n"
                        f"parity: {client.parity}\n"
                        f"baudrate: {client.baudrate}\n\n"

                        f"Ultimo apagado: {last_boot_time}\n"
                        f"Ultimo inicio: {formatted_now}\n"
                        f"{fin}\n")
                send_email(subject, body)
                last_status = estado_de_comunicacion

        # Obtener lecturas del sistema
        uso_cpu = get_cpu_usage()
        porcentaje_uso, espacio_libre, espacio_total = get_disk_usage()
        temperatura = get_temperature()


        # Verificar condiciones criticas del sistema
        if uso_cpu > cpu or porcentaje_uso > memoria_ram or espacio_libre < memoria or temperatura > temperatura_raspberry:
            current_time = dt.datetime.now()
            if (last_email_time is None or (current_time - last_email_time).total_seconds() >= 60):
                if uso_cpu and porcentaje_uso and espacio_libre and temperatura:
                    subject = 'Oficina_Greco-Estado del sistema' #cambiar el asunto del mensaje ------------------------------------------------------------
                    body = (f"Fecha y hora actual: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"Uso de CPU: {uso_cpu}%\n"
                            f"Uso de disco: {porcentaje_uso}%\n"
                            f"Espacio libre en disco: {espacio_libre / (1024**3):.2f} GB\n"
                            f"Temperatura: {temperatura:.2f} °C\n")
                    send_email(subject, body)
                    last_email_time = current_time

        # Verificar el estado de la conexion a Internet
        if not internet_connected:
            if internet_disconnected_time is None:
                internet_disconnected_time = dt.datetime.now()
        else:
            if internet_disconnected_time is not None:
                downtime_duration = dt.datetime.now() - internet_disconnected_time
                subject = 'Oficina_greco-Conexion a Internet Restablecida'#--------------------------------------------------------------------------
                body = (f"Fecha y hora de restablecimiento: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Fecha y hora de desconexion: {internet_disconnected_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"Tiempo de desconexion: {downtime_duration.total_seconds() / 60:.2f} minutos\n")
                send_email(subject, body)
                internet_disconnected_time = None

        # Desconectar despues de la verificacion
        client.close()

        # Esperar 1 minuto antes de la proxima verificacion
        time.sleep(verificacion)

if __name__ == "__main__":
    main()

