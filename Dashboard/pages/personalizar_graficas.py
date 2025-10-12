# personalizar_graficas.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import pickle
import logging
import csv
import plotly.graph_objects as go
import numpy as np
import re
from config import BASE_DIR, CONSUMO_CONFIG_FILE, CONSUMO_CSV_FILE, HEATMAP_DATA_FILE, LOG_DIR
from data_collector import VARIABLES, VARIABLES_DISPLAY, UNITS

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'personalizar_graficas_error.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Funciones de consumo_energia_page.py
def limpiar_valor(valor):
    try:
        return float(valor)
    except (ValueError, TypeError):
        logger.warning(f"Valor no númerico: {valor}")
        return None

@st.cache_data(ttl=3600)
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
            logger.warning(f"No se encontraron datos válidos en {file_path}")
            return pd.DataFrame(columns=['fecha', 'valor'])
        df = pd.DataFrame(contenido, columns=['fecha', 'valor'])
        df = df.sort_values('fecha').dropna().reset_index(drop=True)
        logger.info(f"Datos leídos de {file_path}: {len(df)} filas")
        return df
    except Exception as e:
        logger.error(f"Error leyendo archivo {file_path}: {e}")
        return pd.DataFrame(columns=['fecha', 'valor'])

def calcular_consumo_inicial(fecha_inicio, energia_inicial, usar_valor_energia):
    try:
        fecha_inicio_dt = pd.to_datetime(fecha_inicio)
        if fecha_inicio_dt.date() > datetime.now().date():
            raise ValueError("Fecha de inicio no puede ser futura")
        previous_hour = (datetime.now() - timedelta(hours=1)).replace(minute=59, second=59, microsecond=0)
        previous_hour_file = os.path.join(
            BASE_DIR,
            datetime.now().strftime('%Y-%m-%d'),
            'energia_importada_activa_total',
            f"{previous_hour.strftime('%Y-%m-%d %H')}.txt"
        )
        if usar_valor_energia:
            first_value = energia_inicial
        else:
            first_file = os.path.join(
                BASE_DIR,
                fecha_inicio_dt.strftime('%Y-%m-%d'),
                'energia_importada_activa_total',
                f"{fecha_inicio_dt.strftime('%Y-%m-%d')} 00.txt"
            )
            first_value = None
            if os.path.exists(first_file):
                df_first = read_single_txt_file(first_file)
                if not df_first.empty:
                    first_value = df_first['valor'].iloc[0]
        if first_value is not None and os.path.exists(previous_hour_file):
            df_previous_hour = read_single_txt_file(previous_hour_file)
            if not df_previous_hour.empty:
                last_value_previous_hour = df_previous_hour['valor'].iloc[-1]
                consumo_total = last_value_previous_hour - first_value
                if consumo_total < 0:
                    consumo_total = 0.0
                logger.info(f"Consumo inicial calculado: {consumo_total:.2f} kWh")
                return consumo_total
        logger.warning("No hay datos disponibles para calcular consumo inicial")
        return 0.0
    except ValueError as ve:
        logger.error(f"Error de validacion: {ve}")
        st.error(str(ve))
        return 0.0
    except Exception as e:
        logger.error(f"Error al calcular consumo inicial: {e}")
        return 0.0

def load_consumo_data():
    default_data = {
        'fecha_inicio': 'No disponible',
        'costo_kwh': 3.0,
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
                logger.info(f"Configuración de consumo cargada desde {CONSUMO_CONFIG_FILE}")
                return data
    except Exception as e:
        logger.error(f"Error al cargar {CONSUMO_CONFIG_FILE}: {e}")
    return default_data

def save_consumo_data(fecha_inicio, costo_kwh, energia_inicial, usar_valor_energia, consumo=0.0, costo=0.0, dias_transcurridos=0, consumo_hoy=0.0, costo_hoy=0.0, demanda_maxima=0.0, estimacion_factura=0.0, fecha_fin='No disponible'):
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
        logger.error(f"Error al guardar datos de consumo: {e}")
        st.error(f"Error al guardar la configuracion: {e}")
        return None

# Funciones de historicos_page.py
def generate_historical_graph(variable, start_date, end_date, logger):
    try:
        df = pd.read_csv("/home/pi/Desktop/Medidor/Dashboard/data_buffer.csv")
        df['fecha'] = pd.to_datetime(df['timestamp'])
        df = df[df['fecha'].between(start_date, end_date)]
        if df.empty:
            logger.warning(f"No hay datos disponibles para {variable} en el periodo {start_date} a {end_date}")
            return None
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df['fecha'],
                y=df[variable],
                mode='lines',
                name=VARIABLES_DISPLAY[variable],
                fill='tozeroy'
            )
        )
        # Formatear el titulo con el nombre de la variable, unidades y rango de fechas
        title = f"{VARIABLES_DISPLAY[variable]} ({UNITS.get(variable, '')}), desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
        fig.update_layout(
            title=title,
            title_font=dict(size=14, color="white", family="Arial", weight="normal"),
            margin=dict(t=40, b=0, l=10, r=10),
            xaxis_title="",
            yaxis_title=UNITS.get(variable, ""),
            font=dict(color="white"),
            xaxis=dict(
                tickformat="%b-%d %H:%M",
                tickangle=315,
                tickfont=dict(size=12, color="white", family="Arial"),
                gridcolor="rgba(255, 255, 255, 0.2)",
                showgrid=False,
                ticklabelposition="outside bottom",
                ticklen=5,
                tickwidth=1
            ),
            yaxis=dict(
                title=dict(
                    text=UNITS.get(variable, ''),
                    font=dict(size=10, color="white", family="Arial")
                ),
                tickfont=dict(size=10, color="white", family="Arial"),
                gridcolor="rgba(255, 255, 255, 0.2)",
                showgrid=True
            ),
            plot_bgcolor="#000000",
            paper_bgcolor="#000000",
            height=300
        )
        fig.update_traces(
            line=dict(width=1, color='yellow'),
            fillcolor='rgba(255, 255, 0, 0.2)'
        )
        logger.info(f"Grafico historico generado para {variable} desde {start_date} hasta {end_date}")
        return fig
    except Exception as e:
        logger.error(f"Error generando grafico historico para {variable}: {e}")
        return None


# Funciones de mapa_calor.py
def listar_fechas_disponibles(variable):
    logger.info(f"Listando fechas disponibles para {variable}")
    variable_lower = variable.lower()
    current_hour_file = datetime.now().strftime('%Y-%m-%d %H') + '.txt'
    available_dates = []
    found_directories = []
    for root, dirs, files in os.walk(BASE_DIR):
        date_dir = os.path.basename(os.path.dirname(root))
        if os.path.basename(root).lower() == variable_lower and re.match(r'\d{4}-\d{2}-\d{2}', date_dir):
            found_directories.append(root)
            if any(f.endswith('.txt') and f != current_hour_file for f in files):
                try:
                    date = datetime.strptime(date_dir, '%Y-%m-%d').date()
                    available_dates.append(date)
                except ValueError:
                    logger.warning(f"Directorio con formato inválido: {date_dir}")
    if not found_directories:
        logger.warning(f"No se encontraron directorios para {variable}")
    else:
        logger.info(f"Directorios encontrados para {variable}: {found_directories}")
    if not available_dates:
        logger.warning(f"No se encontraron fechas con datos para {variable}")
        return None, None, []
    available_dates = sorted(available_dates)
    fecha_min = available_dates[0]
    fecha_max = available_dates[-1]
    logger.info(f"Fechas disponibles para {variable}: {[d.strftime('%Y-%m-%d') for d in available_dates]}")
    return fecha_min, fecha_max, available_dates

def load_heatmap_config():
    try:
        if os.path.exists(HEATMAP_DATA_FILE):
            with open(HEATMAP_DATA_FILE, 'rb') as f:
                data = pickle.load(f)
                logger.debug(f"Datos cargados de {HEATMAP_DATA_FILE}: {data.keys()}")
                return {
                    'fig': data.get('fig'),
                    'variable': data.get('variable', 'Potencia_aparente_total'),
                    'fecha_final': data.get('fecha_final', (datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)).strftime('%Y-%m-%d')),
                    'last_update': data.get('last_update'),
                    'manual_config': data.get('manual_config', False)
                }
    except Exception as e:
        logger.error(f"Error al cargar {HEATMAP_DATA_FILE}: {e}")
    return {
        'fig': None,
        'variable': 'Potencia_aparente_total',
        'fecha_final': (datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)).strftime('%Y-%m-%d'),
        'last_update': None,
        'manual_config': False
    }

def save_heatmap_data(fig, variable, fecha_final, manual_config=False):
    try:
        os.makedirs(os.path.dirname(HEATMAP_DATA_FILE), exist_ok=True)
        data = {
            'fig': fig,
            'variable': variable,
            'fecha_final': fecha_final,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'manual_config': manual_config
        }
        with open(HEATMAP_DATA_FILE, 'wb') as f:
            pickle.dump(data, f)
        os.chmod(HEATMAP_DATA_FILE, 0o664)
        logger.info(f"Mapa de calor guardado en {HEATMAP_DATA_FILE}, manual_config={manual_config}")
    except Exception as e:
        logger.error(f"Error al guardar {HEATMAP_DATA_FILE}: {e}")
        raise

@st.cache_data(ttl=3600)
def leer_archivos_txt_por_variable(variable, fecha_inicio=None, fecha_fin=None, exclude_current_hour=True):
    logger.info(f"Leyendo archivos para {variable}")
    contenido_completo = []
    variable_lower = variable.lower()
    current_hour_file = datetime.now().strftime('%Y-%m-%d %H') + '.txt'
    if not os.path.exists(BASE_DIR):
        logger.error(f"Directorio {BASE_DIR} no existe")
        return pd.DataFrame(columns=['fecha', 'valor'])
    if fecha_inicio:
        fecha_inicio = pd.to_datetime(fecha_inicio)
    if fecha_fin:
        fecha_fin = pd.to_datetime(fecha_fin)
        if fecha_fin.hour == 0 and fecha_fin.minute == 0 and fecha_fin.second == 0:
            fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
    found_directories = []
    for root, dirs, files in os.walk(BASE_DIR):
        date_dir = os.path.basename(os.path.dirname(root))
        if os.path.basename(root).lower() != variable_lower:
            continue
        if re.match(r'\d{4}-\d{2}-\d{2}', date_dir):
            found_directories.append(root)
        for archivo in sorted(files):
            if not archivo.endswith('.txt'):
                continue
            if exclude_current_hour and archivo == current_hour_file:
                continue
            try:
                file_datetime = pd.to_datetime(archivo.replace('.txt', ''), format='%Y-%m-%d %H', errors='coerce')
                if pd.isna(file_datetime):
                    logger.warning(f"Nombre de archivo invalido: {archivo}")
                    continue
                if fecha_inicio and fecha_fin:
                    file_end = file_datetime + pd.Timedelta(hours=1) - pd.Timedelta(seconds=1)
                    if file_end < fecha_inicio or file_datetime > fecha_fin:
                        continue
                file_path = os.path.join(root, archivo)
                if not os.access(file_path, os.R_OK):
                    logger.warning(f"Permiso denegado para {file_path}")
                    continue
                df = read_single_txt_file(file_path)
                if not df.empty:
                    if fecha_inicio and fecha_fin:
                        df = df[(df['fecha'] >= fecha_inicio) & (df['fecha'] <= fecha_fin)]
                    contenido_completo.append(df)
            except Exception as e:
                logger.warning(f"Error procesando archivo {archivo} en {root}: {e}")
    if not found_directories:
        logger.warning(f"No se encontraron directorios para {variable}")
    if not contenido_completo:
        logger.warning(f"No se encontraron datos para {variable}")
        return pd.DataFrame(columns=['fecha', 'valor'])
    df = pd.concat(contenido_completo, ignore_index=True)
    df = df.sort_values('fecha').dropna().reset_index(drop=True)
    logger.info(f"Datos leí­dos para {variable}: {len(df)} filas")
    return df

def generate_heatmap(variable, fecha_final, manual_config=False):
    try:
        if isinstance(fecha_final, str):
            fecha_final_dt = datetime.strptime(fecha_final, '%Y-%m-%d')
        else:
            fecha_final_dt = datetime.combine(fecha_final, datetime.min.time())
        fecha_final_dt = fecha_final_dt.replace(hour=23, minute=59, second=59)
        fecha_inicio_dt = fecha_final_dt - timedelta(days=7)
        fecha_min, fecha_max, _ = listar_fechas_disponibles(variable)
        if fecha_min and fecha_inicio_dt.date() < fecha_min:
            fecha_inicio_dt = datetime.combine(fecha_min, datetime.min.time())
        if fecha_max and fecha_final_dt.date() > fecha_max:
            fecha_final_dt = datetime.combine(fecha_max, datetime.min.time()).replace(hour=23, minute=59, second=59)
        # Si no es configuracion manual, asegurarse de no leer la hora actual
        exclude_current_hour = not manual_config
        if not manual_config:
            # Ajustar fecha_final_dt a la hora anterior si es la fecha actual
            now = datetime.now()
            if fecha_final_dt.date() == now.date():
                fecha_final_dt = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        df = leer_archivos_txt_por_variable(variable, fecha_inicio_dt, fecha_final_dt, exclude_current_hour=exclude_current_hour)
        if df.empty:
            logger.error(f"No hay datos para {VARIABLES_DISPLAY[variable]} en el rango")
            st.error("No hay datos disponibles en el rango seleccionado.")
            return None
        df["intervalo"] = df["fecha"].dt.floor('15min').dt.strftime('%H:%M')
        df["fecha_dia"] = df["fecha"].dt.strftime('%b-%d')
        dias_mostrar = [fecha_final_dt.date() - timedelta(days=x) for x in range(7, -1, -1)]
        dias_orden = [d.strftime('%b-%d') for d in dias_mostrar]
        horas = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]
        horas_completas = [f"{h:02d}:00" for h in range(24)]
        base = pd.MultiIndex.from_product([dias_orden, horas], names=["fecha_dia", "intervalo"]).to_frame(index=False)
        heatmap_data = df.groupby(["fecha_dia", "intervalo"])["valor"].mean().reset_index()
        heatmap_full = base.merge(heatmap_data, on=["fecha_dia", "intervalo"], how="left")
        if fecha_final_dt.date() == datetime.now().date() and not manual_config:
            ultima_hora_completa = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
            current_interval = ultima_hora_completa.strftime('%H:%M')
            mask_future = (heatmap_full["fecha_dia"] == dias_orden[0]) & (heatmap_full["intervalo"] > current_interval)
            heatmap_full.loc[mask_future, "valor"] = None
        heatmap_full["fecha_dia"] = pd.Categorical(heatmap_full["fecha_dia"], categories=dias_orden, ordered=True)
        heatmap_full = heatmap_full.sort_values(["fecha_dia", "intervalo"])
        heatmap_pivot = heatmap_full.pivot(index="fecha_dia", columns="intervalo", values="valor")
        heatmap_pivot = heatmap_pivot[horas]
        z_data = np.array(heatmap_pivot.values)
        valid_data = z_data[~np.isnan(z_data)]
        if valid_data.size == 0:
            logger.error("No hay datos validos para generar el mapa de calor")
            st.error("No hay datos validos para generar el mapa de calor.")
            return None
        if variable == 'Voltaje_fase_1':
            zmin = 105
            zmax = 135
            valid_data = valid_data[(valid_data >= 105) & (valid_data <= 135)]
            if valid_data.size == 0:
                logger.error("No hay valores válidos para Voltaje_fase_1 en el rango 105-135 V")
                st.error("No hay valores validos para Voltaje_fase_1 en el rango 105-135 V.")
                return None
        elif variable == 'frecuencia':
            zmin = 59
            zmax = 61
            valid_data = valid_data[(valid_data >= 59) & (valid_data <= 61)]
            if valid_data.size == 0:
                logger.error("No hay valores válidos para frecuencia en el rango 59-61 Hz")
                st.error("No hay valores válidos para frecuencia en el rango 59-61 Hz.")
                return None
        else:
            zmin = 0
            zmax = valid_data.max()
            valid_data = valid_data[valid_data >= 0]
            if valid_data.size == 0:
                logger.error(f"No hay valores validos para {variable} (todos son negativos)")
                st.error(f"No hay valores validos para {variable} (todos son negativos).")
                return None
        if zmin == zmax:
            zmin = zmin - 0.1
            zmax = zmax + 0.1
        logger.info(f"Escala de colores para {variable}: zmin={zmin}, zmax={zmax}")
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=heatmap_pivot.columns.tolist(),
            y=heatmap_pivot.index.tolist(),
            colorscale=[
                [0.0, "rgb(128, 128, 128)"],
                [0.001, "rgb(246, 255, 80)"],
                [0.25, "rgb(252, 206, 80)"],
                [0.5, "rgb(252, 149, 0)"],
                [0.75, "rgb(252, 95, 0)"],
                [1.0, "rgb(252, 0, 0)"]
            ],
            colorbar=dict(title=f"Valor ({UNITS[variable]})", tickformat=".2f"),
            hovertemplate='Dia: %{y}<br>Hora: %{x}<br>Valor: %{z:.2f} ' + UNITS[variable] + '<extra></extra>',
            zmin=zmin,
            zmax=zmax,
            zauto=False,
            connectgaps=False,
            showscale=True
        ))
        fig.update_traces(
            xgap=1,
            ygap=1
        )
        fig.update_layout(
            xaxis=dict(
                tickmode="array",
                tickvals=horas[::4],
                ticktext=horas_completas,
                tickangle=-45,
                tickfont=dict(size=12, color="white"),
                showgrid=False,
                zeroline=False,
                showline=False
            ),
            yaxis=dict(
                tickfont=dict(size=12, color="white", family="Segoe UI"),
                automargin=True,
                ticklabelposition="outside",
                ticklabeloverflow="allow",
                autorange="reversed",
                showgrid=False,
                zeroline=False,
                showline=False
            ),
            title=f"{VARIABLES_DISPLAY[variable]} ({UNITS[variable]}), desde {fecha_inicio_dt.strftime('%Y-%m-%d')} hasta {fecha_final_dt.strftime('%Y-%m-%d')}",
            title_font=dict(size=14, color="white", family="Arial", weight="normal"),
            plot_bgcolor="#000000",
            paper_bgcolor="#000000",
            margin=dict(l=0, r=0, t=40, b=0),
            height=300,
            showlegend=False
        )
        save_heatmap_data(fig, variable, fecha_final_dt.strftime('%Y-%m-%d'), manual_config=manual_config)
        st.success("Mapa de calor generado. Ver el resultado en el panel principal.")
        return fig
    except Exception as e:
        logger.error(f"Error al generar mapa de calor: {e}")
        st.error(f"Error al generar mapa de calor: {e}")
        return None

def run():
    st.set_page_config(page_title="Personalizar Graficas - Medidor CCP", layout="wide")
    st.markdown("""
        <style>
        .stApp {
            background-color: #333333;
            color: white;
        }
        h1, h2, h3, h4, h5, h6, label {
            color: white !important;
        }
        button {
            background-color: #444444 !important;
            color: white !important;
            border-radius: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
    st.title("Personalizar Gráficas")
    # Seccion para configurar consumo
    with st.expander("Configurar Consumo de Energía"):
        consumo_data = load_consumo_data()
        with st.form(key="consumo_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                fecha_inicio = st.date_input(
                    "Fecha de inicio del ciclo de facturación:",
                    value=datetime.now().date() if consumo_data['fecha_inicio'] == 'No disponible' else pd.to_datetime(consumo_data['fecha_inicio']).date(),
                    key="consumo_fecha_inicio",
                    max_value=datetime.now().date()
                )
            with col2:
                costo_kwh = st.number_input(
                    "Costo por kWh (MXN):",
                    min_value=0.0,
                    step=0.01,
                    value=consumo_data['costo_kwh'],
                    key="consumo_costo_kwh"
                )
            with col3:
                energia_inicial = st.number_input(
                    "Energí­a inicial (kWh):",
                    min_value=0.0,
                    step=0.1,
                    value=consumo_data['energia_inicial'],
                    key="consumo_energia_inicial"
                )
                usar_valor_energia = st.checkbox(
                    "Utilizar valor de la energí­a",
                    value=consumo_data['usar_valor_energia'],
                    key="usar_valor_energia"
                )
            col_submit = st.columns(1)[0]
            with col_submit:
                guardar = st.form_submit_button("Guardar Configuración")
            if guardar:
                with st.spinner("Guardando configuración..."):
                    consumo = calcular_consumo_inicial(fecha_inicio.strftime('%Y-%m-%d'), energia_inicial, usar_valor_energia)
                    if consumo is None:
                        return
                    costo = consumo * costo_kwh
                    fecha_fin_dt = datetime.combine(fecha_inicio, datetime.min.time()) + timedelta(days=60)
                    today = datetime.now().date()
                    dias_transcurridos = (today - fecha_inicio).days
                    if dias_transcurridos < 0:
                        dias_transcurridos = 0
                    consumo_data = save_consumo_data(
                        fecha_inicio.strftime('%Y-%m-%d'),
                        costo_kwh,
                        energia_inicial,
                        usar_valor_energia,
                        consumo=consumo,
                        costo=costo,
                        dias_transcurridos=dias_transcurridos,
                        consumo_hoy=0.0,
                        costo_hoy=0.0,
                        demanda_maxima=0.0,
                        estimacion_factura=0.0,
                        fecha_fin=fecha_fin_dt.strftime('%Y-%m-%d')
                    )
                    if consumo_data:
                        st.session_state.consumo_data = consumo_data
                        st.success("Configuración de consumo guardada exitósamente.")
                        logger.info("Configuración de consumo guardada por el usuario")
    # Seccion para configurar graficos historicos
    with st.expander("Configurar Gráficos Históricos"):
        with st.form(key="historicos_form"):
            col_var, col_fecha_inicio, col_fecha_fin = st.columns(3)
            with col_var:
                variable = st.selectbox(
                    "Selecciona variable:",
                    options=VARIABLES,
                    format_func=lambda x: f"{VARIABLES_DISPLAY[x]} ({UNITS.get(x, '')})",
                    key="historicos_variable_select",
                    index=VARIABLES.index("Potencia_activa_Total")
                )
            with col_fecha_inicio:
                fecha_inicio = st.date_input(
                    "Fecha inicial:",
                    value=datetime.now() - timedelta(days=7),
                    key="historicos_fecha_inicio"
                )
            with col_fecha_fin:
                fecha_fin = st.date_input(
                    "Fecha final:",
                    value=datetime.now(),
                    key="historicos_fecha_fin"
                )
            col_submit = st.columns(1)[0]
            with col_submit:
                generar = st.form_submit_button("Generar Gráfico")
            if generar:
                if fecha_inicio > fecha_fin:
                    st.error("La fecha inicial no puede ser mayor que la fecha final.")
                    logger.error("Fecha inicial mayor que fecha final")
                    return
                with st.spinner("Generando gráfico histórico..."):
                    fig = generate_historical_graph(
                        variable,
                        datetime.combine(fecha_inicio, datetime.min.time()),
                        datetime.combine(fecha_fin, datetime.max.time()),
                        logger
                    )
                    if fig:
                        st.session_state.historicos_fig = fig
                        st.success("Gráfico histórico generado. Ver el resultado en el panel principal.")
                    else:
                        st.error("No se pudieron cargar los datos para el gráfico histórico.")
                        logger.error("No se encontraron datos para el gráfico histórico")
    # Seccion para configurar mapa de calor
    with st.expander("Configurar Mapa de Calor"):
        config = load_heatmap_config()
        with st.form(key="heatmap_form"):
            col_var, col_fecha = st.columns(2)
            with col_var:
                variable = st.selectbox(
                    "Selecciona variable:",
                    options=VARIABLES,
                    format_func=lambda x: f"{VARIABLES_DISPLAY[x]} ({UNITS[x]})",
                    key="heatmap_variable_select",
                    index=VARIABLES.index(config['variable'])
                )
            with col_fecha:
                with st.spinner("Cargando fechas disponibles..."):
                    fecha_min, fecha_max, available_dates = listar_fechas_disponibles(variable)
                    if not available_dates:
                        st.error(f"No hay datos disponibles para {VARIABLES_DISPLAY[variable]}.")
                        logger.error(f"No hay fechas disponibles para {variable}")
                        st.form_submit_button("Generar Mapa de Calor", disabled=True)
                        return
                    default_date = datetime.strptime(config['fecha_final'], '%Y-%m-%d').date() if config['fecha_final'] in [d.strftime('%Y-%m-%d') for d in available_dates] else (fecha_max if fecha_max else datetime.now().date())
                fecha_final = st.date_input(
                    "Fecha final:",
                    value=default_date,
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="heatmap_fecha_final",
                    disabled=not bool(available_dates)
                )
            col_submit = st.columns(1)[0]
            with col_submit:
                generar = st.form_submit_button("Generar Mapa de Calor", disabled=not bool(available_dates))
            if generar:
                with st.spinner("Generando mapa de calor..."):
                    fig = generate_heatmap(variable, fecha_final, manual_config=True)
                    if fig:
                        st.session_state.heatmap_fig = fig
                        st.session_state.heatmap_variable = variable
                        st.session_state.fecha_final = fecha_final.strftime('%Y-%m-%d')
                        st.session_state.heatmap_manual_config = True
                        st.session_state.heatmap_last_manual_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        st.success("Mapa de calor generado. Ver el resultado en el panel principal.")
                        logger.info(f"Mapa de calor personalizado generado para {variable} con fecha final {fecha_final}")

if __name__ == "__main__":
    run()
