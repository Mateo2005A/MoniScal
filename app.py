import streamlit as st
import numpy as np
import pandas as pd
import time
import mysql.connector
from datetime import datetime

# --- CONFIGURACIÓN DE CONEXIÓN A MYSQL ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "moniscal_db"
}

def iniciar_base_datos():
    try:
        # Conexión inicial para asegurar que la BD exista
        conn = mysql.connector.connect(host=DB_CONFIG["host"], user=DB_CONFIG["user"], password=DB_CONFIG["password"])
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.commit()
        cursor.close()
        conn.close()

        # Conexión a la BD para asegurar que la tabla exista
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_escalado (
                id INT AUTO_INCREMENT PRIMARY KEY,
                fecha_hora DATETIME,
                trafico_req_s INT,
                derivada_req_s2 FLOAT,
                servidores_activos INT,
                accion_tomada VARCHAR(50)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        st.error(f"Error al conectar con MySQL: {err}")

def guardar_evento(trafico, derivada, servidores, accion):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            INSERT INTO logs_escalado (fecha_hora, trafico_req_s, derivada_req_s2, servidores_activos, accion_tomada)
            VALUES (%s, %s, %s, %s, %s)
        """
        valores = (datetime.now(), trafico, float(derivada), servidores, accion)
        cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error al insertar en MySQL: {err}")

# Inicializar la base de datos de manera automática al cargar el script
iniciar_base_datos()


# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="MoniScal", layout="wide")

st.title("MoniScal: Simulación de Auto-escalado basado en Cálculo Diferencial")
st.write(
    "Este prototipo simula el tráfico web y aplica la **primera derivada** "
    "para predecir la saturación de servidores y levantar la infraestructura de forma proactiva."
)

st.sidebar.header("Parámetros del Sistema")

# --- CONTROL DE PARÁMETROS EN LA BARRA LATERAL ---
tipo_trafico = st.sidebar.selectbox(
    "Selecciona el Escenario de Tráfico:",
    ("Tráfico Normal (Sinusoidal)", "Pico Crítico (Exponencial)")
)

delta_t = st.sidebar.slider("Intervalo de tiempo (Δt en segundos)", 1, 5, 2)
umbral_critico = st.sidebar.slider("Umbral Crítico de la Derivada", 10, 100, 40)
servidores_iniciales = st.sidebar.slider("Servidores Iniciales", 1, 5, 1)

# --- BOTÓN DE INICIO ---
iniciar = st.sidebar.button("Iniciar Simulación")

# --- LÓGICA DE LA SIMULACIÓN ---
if iniciar:
    st.subheader("Monitoreo en Tiempo Real")
    
    metricas_col = st.columns(3)
    kpi_trafico = metricas_col[0].empty()
    kpi_derivada = metricas_col[1].empty()
    kpi_servidores = metricas_col[2].empty()
    
    chart_trafico = st.empty()
    chart_derivada = st.empty()
    
    servidores_activos = servidores_iniciales
    historial_tiempo = []
    historial_trafico = []
    historial_derivada = []
    historial_servidores = []
    
    # Registrar el arranque de la simulación en la BD
    guardar_evento(0, 0.0, servidores_activos, "INICIO_SIMULACION")
    
    for t in range(1, 31):
        if tipo_trafico == "Tráfico Normal (Sinusoidal)":
            trafico_actual = int(50 * np.sin(0.5 * t) + 100)
        else:
            trafico_actual = int(10 * np.exp(0.12 * t) + 50)
            
        if len(historial_trafico) == 0:
            derivada_actual = 0.0
        else:
            trafico_anterior = historial_trafico[-1]
            derivada_actual = (trafico_actual - trafico_anterior) / delta_t
            
        if derivada_actual > umbral_critico:
            servidores_activos += 1
            st.toast(f"¡Alerta! Derivada alta ({derivada_actual:.1f}). Encendiendo servidor.")
            # Guardado automático en MySQL ante escalado ascendente
            guardar_evento(trafico_actual, derivada_actual, servidores_activos, "SCALE_OUT (ENCENDER)")
        elif derivada_actual < -umbral_critico and servidores_activos > servidores_iniciales:
            servidores_activos -= 1
            st.toast(f"Tráfico bajando ({derivada_actual:.1f}). Apagando servidor.")
            # Guardado automático en MySQL ante desescalado descendente
            guardar_evento(trafico_actual, derivada_actual, servidores_activos, "SCALE_IN (APAGAR)")

        # Guardado de datos en MySQL como parte normal del proceso 
        guardar_evento(trafico_actual, derivada_actual, servidores_activos, "PROCESO_SIMULACION")

        # Guardar datos en el historial
        historial_tiempo.append(t)
        historial_trafico.append(trafico_actual)
        historial_derivada.append(derivada_actual)
        historial_servidores.append(servidores_activos)
        
        # Actualizar Métricas en pantalla
        kpi_trafico.metric("Peticiones Actuales", f"{trafico_actual} req/s")
        kpi_derivada.metric("Tasa de Cambio T'(t)", f"{derivada_actual:.1f} req/s²")
        kpi_servidores.metric("Servidores Activos", f"{servidores_activos} uds")
        
        # Actualizar Gráficos
        df_datos = pd.DataFrame({
            "Tiempo (s)": historial_tiempo,
            "Tráfico T(t)": historial_trafico,
            "Derivada T'(t)": historial_derivada,
            "Servidores": historial_servidores
        }).set_index("Tiempo (s)")
        
        chart_trafico.line_chart(df_datos[["Tráfico T(t)", "Servidores"]])
        chart_derivada.line_chart(df_datos["Derivada T'(t)"], color="#FF4B4B")
        
        # Simular el paso del tiempo real
        time.sleep(0.7)
        
    st.success("Simulación finalizada con éxito.")
    
    # --- TABLA DE LOGS DESDE MYSQL AL FINALIZAR ---
    st.write("### Tabla de Logs Registrados en MySQL")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        df_logs = pd.read_sql("SELECT * FROM logs_escalado ORDER BY id DESC LIMIT 10", conn)
        st.dataframe(df_logs, use_container_width=True)
        conn.close()
    except:
        pass
else:
    st.info("Configura los parámetros en el panel izquierdo y haz clic en 'Iniciar Simulación' para visualizar el proceso.")