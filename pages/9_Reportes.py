import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 1. Protección de la Página ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Reportes y Métricas", page_icon="📈", layout="wide")
API_URL = "http://127.0.0.1:8000"

# --- 3. Funciones Auxiliares ---
@st.cache_data(ttl=60) # Cache más largo (60s) porque los reportes no cambian tan rápido
def get_data(endpoint):
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    try:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- 4. Interfaz Principal ---
st.title("📈 Tablero de Control y Reportes")
st.markdown("Métricas clave para la toma de decisiones (Basado en Migración 5).")

# --- PESTAÑAS ---
tab_revenue, tab_vets, tab_alerts = st.tabs(["💰 Ingresos Financieros", "🩺 Desempeño Médico", "🚨 Alertas de Salud"])

# --- TAB 1: INGRESOS ---
with tab_revenue:
    st.subheader("Reporte de Ingresos")
    
    c1, c2 = st.columns(2)
    with c1:
        # Selectores de rango de fecha
        start_date = st.date_input("Fecha Inicio", value=datetime(2025, 1, 1))
        end_date = st.date_input("Fecha Fin", value=datetime.now())
    
    if st.button("Generar Reporte Financiero"):
        # Llamada al endpoint de reporte de ingresos
        report = get_data(f"/reports/revenue?start_date={start_date}&end_date={end_date}")
        
        if report:
            st.divider()
            total = report.get('total_revenue', 0.0)
            
            # Mostrar como métrica grande
            st.metric(label=f"Ingresos Totales ({start_date} a {end_date})", value=f"${total:,.2f}")
            
            # Nota: Si tuvieras datos históricos detallados aquí, podrías mostrar un gráfico de líneas
            st.info("Este total incluye solo las facturas marcadas como 'pagadas' en este periodo.")

# --- TAB 2: VETERINARIOS POPULARES ---
with tab_vets:
    st.subheader("Ranking de Veterinarios")
    st.caption("Basado en el volumen total histórico de citas atendidas.")
    
    vet_stats = get_data("/reports/popular-veterinarians")
    
    if vet_stats:
        # Preparar datos para gráfico
        data = []
        for v in vet_stats:
            # Manejo seguro de campos M5 vs M4
            count = v.get('total_appointments', 0)
            name = f"Dr. {v['last_name']}"
            data.append({"Veterinario": name, "Citas": count, "Rating": v.get('rating', 0.0)})
        
        df_vets = pd.DataFrame(data).sort_values(by="Citas", ascending=False)
        
        # Gráfico de Barras Horizontal
        st.bar_chart(df_vets.set_index("Veterinario")['Citas'], color="#0095f6")
        
        # Tabla detallada
        st.dataframe(
            df_vets,
            column_config={
                "Rating": st.column_config.NumberColumn("⭐ Calificación Promedio", format="%.2f")
            },
            use_container_width=True
        )
    else:
        st.info("No hay datos suficientes para generar el ranking.")

# --- TAB 3: ALERTAS DE VACUNACIÓN ---
with tab_alerts:
    st.subheader("🚨 Pacientes con Vacunas Próximas a Vencer")
    st.write("Listado de mascotas que necesitan refuerzos en los próximos 30 días.")
    
    alerts = get_data("/reports/vaccination-alerts")
    
    if alerts:
        alert_data = []
        for a in alerts:
            # Calcular días restantes
            today = datetime.now().date()
            try:
                due_date = datetime.strptime(a['next_dose_date'], "%Y-%m-%d").date()
                days_left = (due_date - today).days
            except:
                days_left = "?"

            alert_data.append({
                "Mascota": a['pet']['name'],
                "Dueño": f"{a['pet']['owner']['first_name']} {a['pet']['owner']['last_name']}",
                "Email Contacto": a['pet']['owner']['email'],
                "Vacuna": a['vaccine']['name'],
                "Vence el": a['next_dose_date'],
                "Días Restantes": days_left
            })
        
        df_alerts = pd.DataFrame(alert_data).sort_values(by="Vence el")
        
        # Mostrar con estilo de alerta
        st.dataframe(
            df_alerts.set_index("Mascota"),
            column_config={
                "Días Restantes": st.column_config.NumberColumn(
                    "Días",
                    help="Días hasta que venza la vacuna",
                    format="%d ⏳"
                )
            },
            use_container_width=True
        )
        
        if not df_alerts.empty:
            st.warning(f"⚠️ Hay {len(df_alerts)} pacientes que requieren atención este mes.")
    else:
        st.success("✅ No hay alertas de vacunación pendientes para los próximos 30 días.")

# Botón flotante
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")