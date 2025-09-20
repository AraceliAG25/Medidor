import socket
import smtplib
import os
import sys
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import datetime as dt 


# Configuracion del correo
sender_address = "solucionesenergiainnovacion@gmail.com"
sender_password = "psvx asnh vluc rglh"
sender_server = 'smtp.gmail.com'
sender_port = 587
recipient_address = "solucionesenergiainnovacion@gmail.com"


def obtener_penultima_carpeta_por_fecha(ruta):
    try:
        items = os.listdir(ruta)
        #print("esto es ", items)
        # Filtrar solo las carpetas y obtener su fecha de modificacion
        carpetas = []


        for item in items:


            item_path = os.path.join(ruta, item)


            if os.path.isdir(item_path):

                carpetas.append((item))

        if len(carpetas) < 2:



            return "No hay suficientes carpetas para determinar la penultima."



        current_date = dt.date.today() #DIA DE HOY
        #print("formato: ", current_date[0])
        carpetas_datetime = [dt.datetime.strptime(carpeta, '%Y-%m-%d') for carpeta in carpetas]
        carpetas_str = [fecha.strftime('%Y-%m-%d') for fecha in carpetas_datetime]
        carpeta_mas_reciente = max(carpetas_str)
        print("soy la carpeta mas reciente: ", carpeta_mas_reciente)
        penultima_carpeta_mas_reciente = sorted(carpetas_datetime)[-2].strftime('%Y-%m-%d')
        print("soy la carpeta penultima mas reciente: ", penultima_carpeta_mas_reciente)

        return penultima_carpeta_mas_reciente
    except FileNotFoundError:
        return "La ruta especificada no existe."
    except PermissionError:
        return "No tienes permiso para acceder a esta ruta."
    except Exception as e:
        return f"Ocurrio un error: {e}"

ruta = '/home/pi/Desktop/Medidor/Rasp_Greco' #se cambia por la ruta de la ubicacion de la carpeta donde se guardan los cambios----------------------------------


def comprimir_carpeta(ruta_carpeta, archivo_zip):
    nombre_carpeta_principal = os.path.basename(ruta_carpeta.rstrip(os.sep))
    print("NOMBRE CARPETA RAIZ ", nombre_carpeta_principal)
    longitud_carpeta_principal = len(ruta_carpeta.rstrip(os.sep)) + 1


    with zipfile.ZipFile(archivo_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for raiz, dirs, archivos in os.walk(ruta_carpeta):
            for archivo in archivos:
                ruta_completa = os.path.join(raiz, archivo)
                # Crea una ruta relativa que incluye la carpeta principal
                ruta_relativa = os.path.join(nombre_carpeta_principal, ruta_completa[longitud_carpeta_principal:])
                zipf.write(ruta_completa, ruta_relativa)





def send_email_with_attachment(ruta_carpeta):
    penultima_carpeta = obtener_penultima_carpeta_por_fecha(ruta_carpeta)
    if "No hay suficientes carpetas" in penultima_carpeta or "Ocurrió un error" in penultima_carpeta:
        print(penultima_carpeta)
        return



    archivo_zip = 'Data.zip' #-------------------------------------------------------------------------------------
    comprimir_carpeta(os.path.join(ruta_carpeta, penultima_carpeta), archivo_zip)


    try:
        # Crear el mensaje
        msg = MIMEMultipart()
        msg['From'] = sender_address
        msg['To'] = recipient_address
        msg['Subject'] = 'Datos Medidor Rasp_Oficina_Greco'#-------------------------------------------------------------------------


        # Cuerpo del mensaje
        body = "Adjunto encontrarás los datos en una carpeta comprimida."
        msg.attach(MIMEText(body, 'plain'))



        # Adjuntar el archivo ZIP
        with open(archivo_zip, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {archivo_zip}',
            )
            msg.attach(part)


        # Enviar el correo
        server = smtplib.SMTP(sender_server, sender_port)
        server.starttls()
        server.login(sender_address, sender_password)
        server.sendmail(sender_address, recipient_address, msg.as_string())
        server.close()
        print("Mensaje con archivo adjunto enviado con Exito.")


    except Exception as e:
        print(f"Fallo. Error: {e}")
send_email_with_attachment(ruta)


sys.exit()
