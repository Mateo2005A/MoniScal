import streamlit as st
import numpy as np
import pandas as pd
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="MoniScal", layout="wide")

st.title("MoniScal: Sistema de Auto-escalado basado en Cálculo Diferencial")
st.write(
    "Este prototipo simula el tráfico web y aplica la **primera derivada** "
    "para predecir la saturación de servidores y escalar la infraestructura de forma proactiva."
)

st.sidebar.header("Parámetros del Sistema")

# --- CONTROL DE PARÁMETROS EN LA BARRA LATERAL ---
tipo_trafico = st.sidebar.selectbox(
    "Selecciona el Escenario de Tráfico:",
    ("Tráfico Normal (Sinusoidal)", "Pico Crítico (Exponencial)")
)

delta_t = st.sidebar.slider("Intervalo de tiempo (Δt en segundos)", 1, 5, 2)
umbral_critico = st.sidebar.slider("Umbral Crítico de la Derivada (U_crítico)", 10, 100, 40)
servidores_iniciales = st.sidebar.slider("Servidores Iniciales", 1, 5, 1)

# --- BOTÓN DE INICIO ---
iniciar = st.sidebar.button("Iniciar Simulación")

# --- LÓGICA DE LA SIMULACIÓN ---
if iniciar:
    st.subheader("Monitoreo de Infraestructura en Tiempo Real")
    
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
        elif derivada_actual < -umbral_critico and servidores_activos > servidores_iniciales:
            servidores_activos -= 1
            st.toast(f"Tráfico bajando ({derivada_actual:.1f}). Apagando servidor.")
            
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
        
    st.success("Simulación finalizada con éxito. Analiza cómo reaccionó la derivada ante los cambios de pendiente.")
else:
    st.info("Configura los parámetros en el panel izquierdo y haz clic en 'Iniciar Simulación' para ver el prototipo en acción.")