import streamlit as st

# --- Protección de Página (Obligatorio en cada archivo de 'pages/') ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app_streamlit.py") # Si no hay login, patada al inicio

# --- Configuración ---
st.set_page_config(
    page_title="Menú Principal", 
    page_icon="🐾", 
    layout="wide",
    initial_sidebar_state="collapsed" # Ocultamos sidebar para que se vea más "App"
)

# --- Estilos CSS (Tarjetas bonitas) ---
st.markdown("""
<style>
    div[data-testid="stContainer"] {
        background-color: #262730; /* Color de fondo tarjeta */
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #41424C;
        text-align: center;
        transition: transform 0.2s;
        height: 100%;
    }
    div[data-testid="stContainer"]:hover {
        transform: scale(1.02);
        border-color: #0095f6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    h3 { margin-bottom: 0.5rem; color: #FAFAFA; }
    p { color: #A0A0A0; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- Encabezado ---
c1, c2 = st.columns([8, 2])
with c1:
    st.title("🏥 Panel de Control Bigotes y Colas")
    st.caption("Sistema de Gestión Integral v2.0")
with c2:
    st.write("") # Espacio para alinear verticalmente
    if st.button("Cerrar Sesión 🔒", type="primary"):
        st.session_state['logged_in'] = False
        st.session_state['auth_token'] = None
        st.switch_page("app_streamlit.py")

st.divider()

# --- CUADRÍCULA DE NAVEGACIÓN ---

st.subheader("🐾 Gestión Clínica")
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container():
        st.markdown("### 🐶 Mascotas")
        st.markdown("Pacientes, historial y fichas clínicas.")
        if st.button("Ir a Mascotas"):
            st.switch_page("pages/2_Mascotas.py")

with col2:
    with st.container():
        st.markdown("### 👤 Dueños")
        st.markdown("Gestión de clientes y contactos.")
        if st.button("Ir a Dueños"):
            st.switch_page("pages/3_Duenos.py")

with col3:
    with st.container():
        st.markdown("### 📅 Citas")
        st.markdown("Agenda, calendario y emergencias.")
        if st.button("Ir a Citas"):
            st.switch_page("pages/4_Citas.py")

with col4:
    with st.container():
        st.markdown("### 🩺 Veterinarios")
        st.markdown("Personal médico y perfiles.")
        if st.button("Ir a Veterinarios"):
            st.switch_page("pages/5_Veterinarios.py")

st.write("") # Espacio vertical

st.subheader("💉 Inventario y Finanzas")
col5, col6, col7, col8 = st.columns(4)

with col5:
    with st.container():
        st.markdown("### 🧪 Vacunas")
        st.markdown("Catálogo de biológicos disponibles.")
        if st.button("Ir a Vacunas"):
            st.switch_page("pages/6_Vacunas.py")

with col6:
    with st.container():
        st.markdown("### 📋 Registros")
        st.markdown("Historial de aplicaciones de vacunas.")
        if st.button("Ir a Registros"):
            st.switch_page("pages/7_Registros_Vac.py")

with col7:
    with st.container():
        st.markdown("### 💰 Facturas")
        st.markdown("Cobros, pagos y estado de cuenta.")
        if st.button("Ir a Facturas"):
            st.switch_page("pages/8_Facturas.py") # Nota: Ajusta el número si cambia

with col8:
    # Espacio reservado para futuros reportes o configuración
    with st.container():
        st.markdown("### 📈 Reportes")
        st.markdown("Métricas financieras y operativas.")
        # Podrías crear una página de reportes separada
        #if st.button("Ir a Reportes"):
         #   st.switch_page("pages/9_Reportes.py")
        st.button("Próximamente", disabled=True)