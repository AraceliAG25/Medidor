# medidor_dashboard.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
import pickle
from streamlit_autorefresh import st_autorefresh
from data_collector import VARIABLES, VARIABLES_DISPLAY, UNITS
import json
from config import BASE_DIR, CONSUMO_CSV_FILE, HEATMAP_DATA_FILE, LOG_DIR
from pages.personalizar_graficas import generate_heatmap

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'medidor_dashboard_error.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ALERTS_STORAGE_FILE = "/home/pi/Desktop/Medidor/Dashboard/alerts_storage.json"

st.set_page_config(page_title="Tablero Medidor CCP", layout="wide", initial_sidebar_state="expanded")

def generate_gauge_power(data_buffer):
    try:
        if data_buffer.empty or 'Potencia_activa_Total' not in data_buffer.columns:
            logger.warning("No hay datos validos para Potencia_activa_Total, usando valor por defecto")
            data_buffer = pd.DataFrame({
                "timestamp": [datetime.now()],
                "Potencia_activa_Total": [0]
            })
        data_buffer['Potencia_activa_Total'] = pd.to_numeric(data_buffer['Potencia_activa_Total'], errors='coerce').fillna(0)
        last_value = data_buffer['Potencia_activa_Total'].iloc[-1]
        max_value = data_buffer['Potencia_activa_Total'].max()
        gauge_range = max(max_value * 1.2, 10)
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=last_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Potencia Activa (kW)", 'font': {'size': 14, 'color': 'white'}},
            number={'font': {'size': 30, 'color': 'white'}},
            gauge={
                'axis': {'range': [0, gauge_range], 'tickwidth': 1, 'tickcolor': "white", 'tickfont': {'color': 'white'}},
                'bar': {'color': "yellow"},
                'borderwidth': 2,
                'bordercolor': "white",
                'steps': [
                    {'range': [0, gauge_range * 0.6], 'color': "green"},
                    {'range': [gauge_range * 0.6, gauge_range * 0.8], 'color': "orange"},
                    {'range': [gauge_range * 0.8, gauge_range], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': gauge_range * 0.9
                }
            }
        ))
        fig.update_layout(
            font={'color': "white", 'family': "Arial"},
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor="#000000",
            paper_bgcolor="#000000",
            height=150
        )
        logger.info(f"Indicador generado para Potencia_activa_Total: {last_value:.2f} kW")
        return fig
    except Exception as e:
        logger.error(f"Error generando indicador: {e}")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=0,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Potencia Activa (kW)", 'font': {'size': 14, 'color': 'white'}},
            number={'font': {'size': 30, 'color': 'white'}},
            gauge={
                'axis': {'range': [0, 10], 'tickwidth': 1, 'tickcolor': "white", 'tickfont': {'color': 'white'}},
                'bar': {'color': "yellow"},
                'borderwidth': 2,
                'bordercolor': "white",
                'steps': [
                    {'range': [0, 6], 'color': "green"},
                    {'range': [6, 8], 'color': "orange"},
                    {'range': [8, 10], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 9
                }
            }
        ))
        fig.update_layout(
            font={'color': "white", 'family': "Arial"},
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor="#000000",
            paper_bgcolor="#000000",
            height=150
        )
        logger.info("Indicador por defecto generado con valor 0 kW")
        return fig



st.markdown("""
<style>
.stApp {
    background-color: #333333;
    color: white;
    margin-top: 0px !important;
    padding-top: 0px !important;
}

.stSidebar > div {
    background-color: #000000;
}
button[data-testid="stSidebarCollapseButton"] {
    background-color: #FFC107 !important;
    border-radius: 5px;
}
button[data-testid="stSidebarCollapseButton"] > div {
    font-size: 40px !important;
    color: black !important;
}
button[data-testid="stSidebarCollapseButton"] > div::before {
    content: ">>";
    font-size: 40px;
    display: inline-block;
}
h1, h2, h3, h4, h5, h6, label {
    color: white !important;
}
.top-container {
    display: flex;
    justify-content: space-between;
    gap: 2px;
    margin-bottom: 10px;
    width: 100%;
}
.top-card {
    background-color: #2a2a2a;
    border-radius: 8px;
    padding: 12px;
    margin: 4px;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    border: 2px solid #555;
    min-width: 250px;
}
.top-card h3 {
    font-size: 24px !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2;
    text-align: center;
}
.top-card p {
    font-size: 22px !important;
    margin: 5px 0 0 0 !important;
    padding: 0 !important;
    line-height: 1.2;
    text-align: center;
}
.alerts-text {
    color: white !important;
}
.alerts-text-red {
    color: red !important;
}
.metrics-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-gap: 4px;
    height: 180px;
    width: 100%;
}
.metric-card {
    background-color: #2a2a2a;
    border: 2px solid #555;
    border-radius: 8px;
    padding: 12px;
    margin: 5px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 70px;
    width: 100%;
}
.metric-card h3 {
    font-size: 15px !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.2;
    text-align: center;
    color: white !important;
}
.metric-card p {
    font-size: 14px !important;
    margin: 5px 0 0 0 !important;
    padding: 0 !important;
    line-height: 1.2;
    text-align: center;
    color: yellow !important;
}
::-webkit-scrollbar {
    width: 10px;
}
::-webkit-scrollbar-thumb {
    background-color: #555;
    border-radius: 10px;
}
div[data-testid="stSidebarNav"] {
    display: none !important;
}
div[data-testid="stSelectbox"] select {
    background-color: #444444 !important;
    color: white !important;
    border-radius: 5px;
}
.selectbox-container {
    width: 100% !important;
}
.selectbox-container-var {
    width: 66.66% !important;
}
.selectbox-container-time {
    width: 33.33% !important;
}
.selectbox-row {
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    flex-direction: column;
}
.plotly-graph-div {
    margin: 0 !important;
    padding: 0 !important;
}
/* Elimina padding superior del contenedor principal */
div.block-container {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}

/* Tambin fuerza el body a quitar margen y padding */
html, body {
    margin: 0 !important;
    padding: 0 !important;
}

/* Ajusta el contenedor principal de la pgina */
section.main > div {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
}
</style>
""", unsafe_allow_html=True)


PAGES = {
    "Ventana Principal": "pages.tiempo_real",
    "Personalizar GrÃ¡ficas": "pages.personalizar_graficas",
    "Alertas": "pages.alertas_page",
    "InformaciÃ³n": "pages.informacion_page"
}

if 'heatmap_fig' not in st.session_state:
    st.session_state.heatmap_fig = None
if 'consumo_data' not in st.session_state:
    st.session_state.consumo_data = {}
if 'historicos_fig' not in st.session_state:
    st.session_state.historicos_fig = None
if 'var1' not in st.session_state:
    st.session_state.var1 = "Corriente_linea1"
if 'var2' not in st.session_state:
    st.session_state.var2 = "Potencia_activa_Total"
if 'time_range_var1' not in st.session_state:
    st.session_state.time_range_var1 = "Hora"
if 'time_range_var2' not in st.session_state:
    st.session_state.time_range_var2 = "Hora"
if 'heatmap_last_manual_update' not in st.session_state:
    st.session_state.heatmap_last_manual_update = None

def get_file_path(variable, date, hour):
    date_str = date.strftime("%Y-%m-%d")
    hour_str = hour.strftime("%Y-%m-%d %H")
    directory = os.path.join(BASE_DIR, date_str, variable.lower())
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, f"{hour_str}.txt")
    return file_path

def initialize_default_heatmap():
    variable = "Potencia_aparente_total"
    fecha_final = (datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)).date()
    fecha_final_str = fecha_final.strftime('%Y-%m-%d')
    logger.info(f"Inicializando mapa de calor por defecto para {variable} con fecha final {fecha_final_str}")
    fig = generate_heatmap(variable, fecha_final_str, manual_config=False)
    if fig:
        st.session_state.heatmap_fig = fig
        st.session_state.heatmap_variable = variable
        st.session_state.fecha_final = fecha_final_str
        st.session_state.heatmap_manual_config = False
        st.session_state.heatmap_last_manual_update = None
        logger.info("Mapa de calor por defecto inicializado")
    else:
        logger.warning("No se pudo generar mapa de calor por defecto")
        st.session_state.heatmap_fig = None

def load_heatmap_fig():
    try:
        now = datetime.now()
        # Verificar si el mapa de calor personalizado ha expirado
        if st.session_state.get('heatmap_manual_config', False) and st.session_state.get('heatmap_last_manual_update'):
            last_update = datetime.strptime(st.session_state.heatmap_last_manual_update, '%Y-%m-%d %H:%M:%S')
            next_update_hour = last_update.replace(minute=5, second=0, microsecond=0) + timedelta(hours=1)
            if now >= next_update_hour:
                logger.info("Mapa de calor personalizado ha expirado, inicializando mapa por defecto")
                initialize_default_heatmap()
        # Cargar configuracion existente
        if os.path.exists(HEATMAP_DATA_FILE):
            with open(HEATMAP_DATA_FILE, 'rb') as f:
                data = pickle.load(f)
                fig = data.get('fig')
                variable = data.get('variable', 'Potencia_aparente_total')
                fecha_final = data.get('fecha_final', (datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)).strftime('%Y-%m-%d'))
                manual_config = data.get('manual_config', False)
                if fig is None:
                    logger.error(f"No se encontro figura valida en {HEATMAP_DATA_FILE}")
                    initialize_default_heatmap()
                    return st.session_state.heatmap_fig
                fecha_final_dt = datetime.strptime(fecha_final, '%Y-%m-%d')
                fecha_inicio_dt = fecha_final_dt - timedelta(days=7)
                fig.update_layout(
                    xaxis_title='',
                    yaxis_title='',
                    title=f"{VARIABLES_DISPLAY[variable]} ({UNITS[variable]}), desde {fecha_inicio_dt.strftime('%Y-%m-%d')} hasta {fecha_final_dt.strftime('%Y-%m-%d')}",
                    title_font=dict(size=14, color="white", family="Arial", weight="normal"),
                    plot_bgcolor="#000000",
                    paper_bgcolor="#000000",
                    margin=dict(l=0, r=0, t=40, b=0),
                    xaxis=dict(
                        tickangle=-45,
                        tickmode="array",
                        tickfont=dict(size=12, color="white"),
                        showgrid=False,
                        zeroline=False,
                        showline=False
                    ),
                    yaxis=dict(
                        tickmode="array",
                        tickfont=dict(size=12, color="white", family="Segoe UI"),
                        automargin=True,
                        ticklabelposition="outside",
                        ticklabeloverflow="allow",
                        autorange="reversed",
                        showgrid=False,
                        zeroline=False,
                        showline=False
                    ),
                    height=300,
                    showlegend=False
                )
                st.session_state.heatmap_fig = fig
                st.session_state.heatmap_variable = variable
                st.session_state.fecha_final = fecha_final
                st.session_state.heatmap_manual_config = manual_config
                logger.info(f"Mapa de calor cargado desde {HEATMAP_DATA_FILE}")
                return fig
        else:
            logger.warning(f"Archivo {HEATMAP_DATA_FILE} no existe, inicializando mapa por defecto")
            initialize_default_heatmap()
            return st.session_state.heatmap_fig
    except Exception as e:
        logger.error(f"Error al cargar {HEATMAP_DATA_FILE}: {str(e)}")
        initialize_default_heatmap()
        return st.session_state.heatmap_fig

def load_data_buffer():
    try:
        data_buffer_file = "/home/pi/Desktop/Medidor/Dashboard/data_buffer.csv"
        persistent_buffer_file = "/home/pi/Desktop/Medidor/Dashboard/persistent_buffer.csv"
        df = None
        if os.path.exists(data_buffer_file):
            df = pd.read_csv(data_buffer_file)
            logger.info(f"Cargado {data_buffer_file} con {len(df)} filas")
        elif os.path.exists(persistent_buffer_file):
            df = pd.read_csv(persistent_buffer_file)
            logger.info(f"Cargado {persistent_buffer_file} con {len(df)} filas")
        else:
            logger.warning(f"No existe {data_buffer_file} ni {persistent_buffer_file}")
            return pd.DataFrame({
                "timestamp": [datetime.now()],
                "Potencia_activa_Total": [0]
            })
        if 'Potencia_activa_Total' in df.columns:
            df['Potencia_activa_Total'] = pd.to_numeric(df['Potencia_activa_Total'], errors='coerce').fillna(0)
        else:
            logger.warning("Columna Potencia_activa_Total no encontrada, agregando con ceros")
            df['Potencia_activa_Total'] = 0
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors='coerce')
        df = df.dropna(subset=["timestamp"]).reset_index(drop=True)
        if df.empty:
            logger.warning("No hay datos validos, retornando datos por defecto")
            return pd.DataFrame({
                "timestamp": [datetime.now()],
                "Potencia_activa_Total": [0]
            })
        logger.info(f"Datos procesados: {len(df)} filas validas")
        return df
    except Exception as e:
        logger.error(f"Error al leer CSV: {e}")
        st.error(f"Error al cargar datos en tiempo real: {e}")
        return pd.DataFrame({
            "timestamp": [datetime.now()],
            "Potencia_activa_Total": [0]
        })

def load_consumo_metrics():
    default_data = {
        'fecha_inicio': 'No disponible',
        'fecha_fin': 'No disponible',
        'dias_transcurridos': 0,
        'consumo_hoy': 0.0,
        'costo_hoy': 0.0,
        'demanda_maxima': 0.0,
        'consumo_acumulado': 0.0,
        'costo_acumulado': 0.0,
        'estimacion_factura': 0.0
    }
    try:
        if os.path.exists(CONSUMO_CSV_FILE):
            df = pd.read_csv(CONSUMO_CSV_FILE, usecols=[
                'fecha_inicio', 'fecha_fin', 'dias_transcurridos', 'consumo_hoy',
                'costo_hoy', 'demanda_maxima', 'consumo_acumulado', 'costo_acumulado',
                'estimacion_factura'
            ])
            if not df.empty:
                data = df.iloc[0].to_dict()
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                        logger.warning(f"Clave {key} no encontrada en {CONSUMO_CSV_FILE}, usando valor por defecto: {default_data[key]}")
                logger.info(f"Datos de consumo cargados desde {CONSUMO_CSV_FILE}")
                return data
    except Exception as e:
        logger.error(f"Error al cargar {CONSUMO_CSV_FILE}: {e}")
    return default_data

def load_alerts_count():
    try:
        with open(ALERTS_STORAGE_FILE, 'r') as f:
            alerts = json.load(f)
        return len(alerts)
    except Exception as e:
        logger.error(f"Error cargando conteo de alertas: {e}")
        return 0

def initialize_default_historical_graph():
    variable = "Potencia_activa_Total"
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    from pages.personalizar_graficas import generate_historical_graph
    fig = generate_historical_graph(variable, start_date, end_date, logger)
    if fig is not None:
        st.session_state.historicos_fig = fig
        logger.info("Grafica historica por defecto generada para Potencia_activa_Total (Dia)")
    else:
        logger.warning("No se pudo generar grafica historica por defecto")
        st.session_state.historicos_fig = None

def generate_time_series_plot(data_buffer, variable, time_range):
    try:
        if data_buffer.empty or variable not in data_buffer.columns:
            logger.warning(f"No hay datos disponibles para {variable}")
            return None
        df_plot = data_buffer[["timestamp", variable]].dropna(subset=[variable])
        if df_plot.empty:
            logger.warning(f"No hay datos validos para {variable}")
            return None
        if time_range == "Hora":
            time_delta = timedelta(hours=1)
            target_points = 720
        elif time_range == "Dia":
            time_delta = timedelta(days=1)
            target_points = 720
        elif time_range == "Semana":
            time_delta = timedelta(days=7)
            target_points = 720
        else:
            time_delta = timedelta(days=30)
            target_points = 720
        start_time = datetime.now() - time_delta
        df_plot = df_plot[df_plot["timestamp"] >= start_time]
        if df_plot.empty:
            logger.warning(f"No hay datos en rango {time_range} para {variable}")
            return None
        if time_range != "Hora" and len(df_plot) > target_points:
            step = max(1, len(df_plot) // target_points)
            df_plot = df_plot.iloc[::step].reset_index(drop=True)
        valid_data = df_plot[variable][df_plot[variable].notnull()]
        y_min = 0
        y_max = valid_data.max() * 1.1 if valid_data.size > 0 else 10
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_plot["timestamp"],
                y=df_plot[variable],
                mode='lines',
                name=VARIABLES_DISPLAY[variable],
                connectgaps=False,
                fill='tozeroy',
                fillcolor='rgba(0, 176, 246, 0.2)'
            )
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            font=dict(color="white"),
            yaxis=dict(
                title=dict(
                    text=UNITS.get(variable, ''),
                    font=dict(size=14, color="white", family="Arial")
                ),
                tickfont=dict(size=14, color="white", family="Arial"),
                range=[y_min, y_max],
                autorange=False
            ),
            xaxis=dict(
                tickformat="%H:%M:%S" if time_range == "Hora" else "%b-%d %H:%M",
                tickangle=315,
                nticks=10,
                range=[start_time, datetime.now()],
                tickfont=dict(size=12, family='Arial', color='white')
            ),
            plot_bgcolor="#000000",
            paper_bgcolor="#000000",
            height=200
        )
        logger.info(f"Grafica generada para {variable} en rango {time_range}")
        return fig
    except Exception as e:
        logger.error(f"Error generando grafica para {variable}: {e}")
        return None

def dashboard():
    st_autorefresh(interval=30000, key="refresh_realtime")  # Cambiado a 30 segundos
    st.sidebar.title("NavegaciÃ³n")
    selection = st.sidebar.radio("Ir a:", list(PAGES.keys()))
    if selection != "Ventana Principal":
        try:
            page_module = __import__(PAGES[selection], fromlist=[""])
            page_module.run()
            st.stop()
        except Exception as e:
            logger.error(f"Error cargando pagina {selection}: {e}")
            st.error(f"Error cargando pagina: {e}")
            st.stop()
    consumo_data = load_consumo_metrics()
    if st.session_state.historicos_fig is None:
        initialize_default_historical_graph()
    data_buffer = load_data_buffer()
    last_update_time = "No disponible"
    potencia_activa_actual = 0
    alerts_count = load_alerts_count()
    alerts_class = "alerts-text-red" if alerts_count > 0 else "alerts-text"
    if not data_buffer.empty:
        last_timestamp = data_buffer["timestamp"].max()
        if pd.notna(last_timestamp):
            last_update_time = last_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if "Potencia_activa_Total" in data_buffer.columns:
            last_data = data_buffer[data_buffer["timestamp"] == last_timestamp]
            if not last_data.empty:
                potencia_activa_actual = last_data["Potencia_activa_Total"].iloc[0]
    st.markdown(
        """
        <div class="top-container">
            <div class="top-card">
                <p>{0}</p>
            </div>
            <div class="top-card">
                <h3>Medidor Oficina Del Greco</h3>
            </div>
            <div class="top-card">
                <p class="{1}">Alertas sin atender: {2}</p>
            </div>
        </div>
        """.format(last_update_time, alerts_class, alerts_count),
        unsafe_allow_html=True
    )
    col1, col2, col3 = st.columns([1, 1, 1])
    if consumo_data['fecha_inicio'] != 'No disponible':
        fecha_inicio = consumo_data['fecha_inicio']
        fecha_fin = consumo_data['fecha_fin']
        dias_transcurridos = consumo_data['dias_transcurridos']
        consumo_hoy = consumo_data['consumo_hoy']
        costo_hoy = consumo_data['costo_hoy']
        demanda_maxima = consumo_data['demanda_maxima']
        consumo_acumulado = consumo_data['consumo_acumulado']
        costo_acumulado = consumo_data['costo_acumulado']
        estimacion_factura = consumo_data['estimacion_factura']
        with col1:
            st.markdown(
                """
                <div class="metrics-column">
                    <div class="metric-card">
                        <h3>Ciclo de facturaciÃ³n actual:</h3>
                        <p>{0} hasta {1}</p>
                    </div>
                    <div class="metric-card">
                        <h3>DÃ­as transcurridos en periodo:</h3>
                        <p>{2} dÃ­as</p>
                    </div>
                    <div class="metric-card">
                        <h3>Consumo hoy:</h3>
                        <p>{3:.2f} kWh</p>
                    </div>
                    <div class="metric-card">
                        <h3>Costo hoy:</h3>
                        <p>${4:.2f} MXN</p>
                    </div>
                </div>
                """.format(fecha_inicio, fecha_fin, dias_transcurridos, consumo_hoy, costo_hoy),
                unsafe_allow_html=True
            )
        with col2:
            gauge_fig = generate_gauge_power(data_buffer)
            if gauge_fig is not None:
                st.plotly_chart(gauge_fig, use_container_width=True)
            else:
                st.warning("No hay datos disponibles para el indicador de Potencia Activa Total")
                logger.warning("No se pudo cargar datos para el indicador")
        with col3:
            st.markdown(
                """
                <div class="metrics-column">
                    <div class="metric-card">
                        <h3>Demanda mÃ¡xima en periodo:</h3>
                        <p>{0:.2f} kW</p>
                    </div>
                    <div class="metric-card">
                        <h3>Consumo acumulado:</h3>
                        <p>{1:.2f} kWh</p>
                    </div>
                    <div class="metric-card">
                        <h3>Costo acumulado:</h3>
                        <p>${2:.2f} MXN</p>
                    </div>
                    <div class="metric-card">
                        <h3>EstimaciÃ³n proxima factura:</h3>
                        <p>${3:.2f} MXN</p>
                    </div>
                </div>
                """.format(
                    demanda_maxima,
                    consumo_acumulado,
                    costo_acumulado,
                    estimacion_factura
                ),
                unsafe_allow_html=True
            )
    else:
        with col1:
            st.markdown(
                """
                <div class="metrics-column">
                    <div class="metric-card">
                        <h3>Ciclo de facturacion actual:</h3>
                        <p>Configurar datos de consumo</p>
                    </div>
                    <div class="metric-card">
                        <h3>Dias transcurridos en periodo:</h3>
                        <p>Configurar datos de consumo</p>
                    </div>
                    <div class="metric-card">
                        <h3>Consumo hoy:</h3>
                        <p>0 kWh</p>
                    </div>
                    <div class="metric-card">
                        <h3>Costo hoy:</h3>
                        <p>$0.00 MXN</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            gauge_fig = generate_gauge_power(data_buffer)
            if gauge_fig is not None:
                st.plotly_chart(gauge_fig, use_container_width=True)
            else:
                st.warning("No hay datos disponibles para el indicador de Potencia Activa Total")
                logger.warning("No se pudo cargar datos para el indicador")
        with col3:
            st.markdown(
                """
                <div class="metrics-column">
                    <div class="metric-card">
                        <h3>Demanda maxima en periodo:</h3>
                        <p>0 kW</p>
                    </div>
                    <div class="metric-card">
                        <h3>Consumo acumulado:</h3>
                        <p>Configurar datos de consumo</p>
                    </div>
                    <div class="metric-card">
                        <h3>Costo acumulado:</h3>
                        <p>Configurar datos de consumo</p>
                    </div>
                    <div class="metric-card">
                        <h3>Estimacion proxima factura:</h3>
                        <p>Configurar datos de consumo</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.info("Configurar datos de consumo en la pÃ¡gina Personalizar GrÃ¡ficas")
    col1, col2 = st.columns(2)
    with col1:
        col_select_var, col_select_time = st.columns([2, 1])
        with col_select_var:
            var1 = st.selectbox(
                label="Variable 1",
                options=VARIABLES,
                format_func=lambda x: f"{VARIABLES_DISPLAY[x]} ({UNITS.get(x, '')})",
                key="var1",
                index=VARIABLES.index(st.session_state.var1),
                label_visibility="collapsed"
            )
        with col_select_time:
            time_range_var1 = st.selectbox(
                label="Rango de tiempo 1",
                options=["Hora", "Dia", "Semana", "Mes"],
                index=["Hora", "Dia", "Semana", "Mes"].index(st.session_state.time_range_var1),
                key="time_range_var1",
                label_visibility="collapsed"
            )
            st.empty()
        fig1 = generate_time_series_plot(data_buffer, var1, st.session_state.time_range_var1)
        if fig1 is not None:
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.warning(f"No hay datos disponibles para {VARIABLES_DISPLAY[var1]} en el rango seleccionado")
            logger.warning(f"No hay datos para {var1} en rango {st.session_state.time_range_var1}")
    with col2:
        col_select_var, col_select_time = st.columns([2, 1])
        with col_select_var:
            var2 = st.selectbox(
                label="Variable 2",
                options=VARIABLES,
                format_func=lambda x: f"{VARIABLES_DISPLAY[x]} ({UNITS.get(x, '')})",
                key="var2",
                label_visibility="collapsed"
            )
        with col_select_time:
            time_range_var2 = st.selectbox(
                label="Rango de tiempo 2",
                options=["Hora", "Dia", "Semana", "Mes"],
                index=["Hora", "Dia", "Semana", "Mes"].index(st.session_state.time_range_var2),
                key="time_range_var2",
                label_visibility="collapsed"
            )
            st.empty()
        fig2 = generate_time_series_plot(data_buffer, var2, st.session_state.time_range_var2)
        if fig2 is not None:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning(f"No hay datos disponibles para {VARIABLES_DISPLAY[var2]} en el rango seleccionado")
            logger.warning(f"No hay datos para {var2} en rango {st.session_state.time_range_var2}")
    col1, col2 = st.columns(2)
    with col1:
        heatmap_fig = load_heatmap_fig()
        if heatmap_fig is not None:
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.error("No se pudo cargar el mapa de calor. Configuralo en la pÃ¡gina Personalizar GrÃ¡ficas.")
            logger.error("Mapa de calor no encontrado o archivo heatmap_data.pkl corrupto")
    with col2:
        if st.session_state.historicos_fig is not None:
            variable = "Potencia_activa_Total"
            if st.session_state.historicos_fig.data:
                variable = next((var for var, display in VARIABLES_DISPLAY.items() if display == st.session_state.historicos_fig.data[0].name), variable)
            st.session_state.historicos_fig.update_layout(
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
            st.session_state.historicos_fig.update_traces(
                line=dict(width=1, color='yellow'),
                fillcolor='rgba(255, 255, 0, 0.2)'
            )
            st.plotly_chart(st.session_state.historicos_fig, use_container_width=True)
        else:
            st.warning("No se pudieron cargar datos historicos para Potencia Activa Total.")
            logger.warning("No se encontraron datos para la grafica historica por defecto")

def run():
    dashboard()

if __name__ == "__main__":
    run()
