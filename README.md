# Instalación del Sistema de Monitoreo SE

Este repositorio contiene el código necesario para implementar un sistema de monitoreo en una Raspberry Pi. A continuación, se detallan los pasos para preparar el entorno e instalar las dependencias necesarias.

##  Requisitos Previos

- Raspberry Pi con sistema operativo basado en Debian (Raspberry Pi OS)
- Python 3 instalado

## Instalar Git en la Raspberry Pi

Antes de clonar el repositorio, asegúrate de tener Git instalado en tu Raspberry Pi. Para ello, ejecuta:

```
sudo apt update
sudo apt install git -y
```
##  Instalación del Entorno Virtual
Pra clonar el repositorio necesitamos ubicarno en el Desktop de nuetra rapberry, ejecuta el siguiente comando 
```
cd Desktop
```
Cuando te ubiques en tu Destop puedes clonar el repositorio con el siguiente comando
```
git clone https://github.com/AraceliAG25/Medidor.git
```

Te creará una carpeta con el nombre Medidor-main
cambia el nombre de la carpeta como Medidor

luego ejecuta el sigiente comando en una nueva terminal
```
cd Desktop
cd Medidor
```

Después de clonar este repositorio, se debe crear un entorno virtual para manejar las dependencias del proyecto de manera aislada.

### 1. Actualizar el sistema y asegurarse de tener `python3-venv`:

```
sudo apt update
sudo apt install python3-venv -y
```

## 2️ Crear y activar el entorno virtual

Ejecuta los siguientes comandos en la terminal para crear y activar el entorno virtual:

```
python3 -m venv venv
source venv/bin/activate

```

## 3️ Instalar las dependencias

Con el entorno virtual activado, instala las dependencias necesarias para el proyecto ejecutando el siguiente comando:

```bash
pip install -r requirements.txt
```
