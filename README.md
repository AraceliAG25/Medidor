# InstalacionSistemaMonitoreoSE
Instalación de códigos para sistema de monitoreo


# Entorno virtual
Después de haber clonado el repositorio, se debe crear un entorno virtual para
nuestras librerías, para ello debemos de ejecutar lo siguiente dentro de nuestra Raspi

sudo apt update
sudo apt install python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


