# update_heatmap_cron.py
import logging
import os
from datetime import datetime, timedelta
from pages.personalizar_graficas import generate_heatmap, load_heatmap_config, save_heatmap_data
from config import BASE_DIR, LOG_DIR

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'update_heatmap_cron.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_data_availability(variable, fecha_final):
    # Verificar si existe el archivo de la hora anterior
    fecha_final_dt = datetime.strptime(fecha_final, '%Y-%m-%d') if isinstance(fecha_final, str) else fecha_final
    previous_hour = fecha_final_dt.replace(hour=fecha_final_dt.hour, minute=0, second=0, microsecond=0)
    file_path = os.path.join(
        BASE_DIR,
        previous_hour.strftime('%Y-%m-%d'),
        variable.lower(),
        f"{previous_hour.strftime('%Y-%m-%d %H')}.txt"
    )
    if os.path.exists(file_path):
        logger.info(f"Archivo encontrado: {file_path}")
        return True
    logger.warning(f"No se encontro archivo para {variable} en {file_path}")
    return False

def update_heatmap():
    try:
        now = datetime.now()
        # Verificar si son los primeros 5 minutos de la hora
        if now.minute != 5:
            logger.info(f"Ejecucion cancelada: no son los 5 minutos de la hora (minuto actual: {now.minute})")
            return
        logger.info("Iniciando actualizacion automatica del mapa de calor")
        variable = 'Potencia_aparente_total'
        # Usar la hora anterior como fecha final
        fecha_final_dt = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        fecha_final_str = fecha_final_dt.strftime('%Y-%m-%d')
        # Verificar si hay datos disponibles
        if not check_data_availability(variable, fecha_final_str):
            logger.error(f"No hay datos disponibles para {variable} en la hora anterior ({fecha_final_str})")
            return
        # Generar mapa de calor
        fig = generate_heatmap(variable, fecha_final_str, manual_config=False)
        if fig:
            save_heatmap_data(fig, variable, fecha_final_str, manual_config=False)
            logger.info(f"Mapa de calor actualizado para {variable} con fecha final {fecha_final_str}")
        else:
            logger.error(f"No se pudo generar el mapa de calor para {variable} en {fecha_final_str}")
    except Exception as e:
        logger.error(f"Error en la actualizacion del mapa de calor: {e}")

if __name__ == "__main__":
    update_heatmap()
