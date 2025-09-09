# Instalación del Sistema de Monitoreo SE

Este repositorio contiene el código necesario para implementar un sistema de monitoreo en una Raspberry Pi. A continuación, se detallan los pasos para preparar el entorno e instalar las dependencias necesarias.

## 📦 Requisitos Previos

- Raspberry Pi con sistema operativo basado en Debian (Raspberry Pi OS)
- Python 3 instalado

##  Instalación del Entorno Virtual

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
