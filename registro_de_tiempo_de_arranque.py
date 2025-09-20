import os
import datetime


# Archivo de registro
log_file = '/var/log/boot_time.log'


# Registra la hora de arranque
def log_boot_time():
    with open(log_file, 'a') as f:
        boot_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        f.write(f'Started: {boot_time}\n')


if __name__ == "__main__":
    log_boot_time()

