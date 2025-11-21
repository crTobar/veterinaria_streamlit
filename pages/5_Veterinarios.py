import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# --- 1. Protección de la Página ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión de Veterinarios", page_icon="🩺", layout="wide")
API_URL = "http://127.0.0.1:8000"

# --- 3. Funciones Auxiliares ---
@st.cache_data(ttl=5)
def get_data(endpoint):
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    try:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error de conexión: {e}")
        return []

def api_request(method: str, endpoint: str, data: dict = None):
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    try:
        if method == "POST":
            response = requests.post(f"{API_URL}{endpoint}", headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(f"{API_URL}{endpoint}", headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(f"{API_URL}{endpoint}", headers=headers)
        
        response.raise_for_status()
        if response.status_code != 204:
            return response.json()
        return True
    except requests.exceptions.RequestException as e:
        try:
            error_detail = response.json().get('detail', str(e))
        except:
            error_detail = str(e)
        st.error(f"Error: {error_detail}")
        return None

# --- 4. Interfaz Principal ---
st.title("🩺 Gestión de Personal Médico")

# Cargar datos
vets_list = get_data("/veterinarians/")
if not vets_list:
    vets_list = [] # Evitar errores si está vacío

# Mapeo para el selector
vet_options = {f"{v['veterinarian_id']} - Dr. {v['first_name']} {v['last_name']}": v['veterinarian_id'] for v in vets_list}

# --- PESTAÑAS ---
tab_directory, tab_create, tab_manage = st.tabs(["📋 Directorio", "➕ Registrar Nuevo", "✏️ Detalles y Edición"])

# --- TAB 1: DIRECTORIO ---
with tab_directory:
    st.subheader("Directorio de Especialistas")
    
    if vets_list:
        # Filtros
        col_search, col_spec = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("🔍 Buscar por Nombre, Licencia o Email:", placeholder="Escribe aquí...")
        
        # Obtener especializaciones únicas
        specs = list(set([v.get('specialization') for v in vets_list if v.get('specialization')]))
        with col_spec:
            spec_filter = st.selectbox("Especialización", ["Todas"] + specs)

        df_vets = pd.DataFrame(vets_list)
        
        # Filtrado
        if search_term:
            df_vets = df_vets[
                df_vets['first_name'].str.contains(search_term, case=False) |
                df_vets['last_name'].str.contains(search_term, case=False) |
                df_vets['license_number'].str.contains(search_term, case=False) |
                df_vets['email'].str.contains(search_term, case=False)
            ]
        if spec_filter != "Todas":
            df_vets = df_vets[df_vets['specialization'] == spec_filter]

        # Configuración de columnas
        display_cols = ["veterinarian_id", "first_name", "last_name", "specialization", "phone", "email", "is_active"]
        column_config = {
            "first_name": "Nombre", "last_name": "Apellido",
            "specialization": "Especialidad", "phone": "Teléfono",
            "is_active": st.column_config.CheckboxColumn("Activo", disabled=True)
        }

        if 'rating' in df_vets.columns:
            display_cols.extend(["rating", "consultation_fee"])
            column_config["rating"] = st.column_config.NumberColumn("⭐ Rating", format="%.2f")
            column_config["consultation_fee"] = st.column_config.NumberColumn("💲 Tarifa", format="$%.2f")

        st.dataframe(
            df_vets[display_cols].set_index("veterinarian_id"),
            column_config=column_config,
            width='stretch'
        )
    else:
        st.info("No hay veterinarios registrados.")

# --- TAB 2: REGISTRAR NUEVO (LA PARTE NUEVA) ---
with tab_create:
    st.subheader("Alta de Nuevo Veterinario")
    st.write("Complete los datos para registrar un nuevo médico en el sistema.")
    
    with st.form("new_vet_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_first = st.text_input("Nombre*")
            new_email = st.text_input("Email (Usuario)*")
            new_license = st.text_input("N° de Licencia*")
            new_spec = st.text_input("Especialización")
            new_fee = st.number_input("Tarifa Consulta ($)", min_value=0.0, format="%.2f")

        with c2:
            new_last = st.text_input("Apellido*")
            new_phone = st.text_input("Teléfono")
            new_pass = st.text_input("Contraseña (para Login)*", type="password")
            new_hire = st.date_input("Fecha Contratación", value=date.today())
            new_active = st.checkbox("Cuenta Activa", value=True)

        submitted_create = st.form_submit_button("Registrar Veterinario")
        
        if submitted_create:
            if not new_first or not new_last or not new_email or not new_pass or not new_license:
                st.error("Todos los campos marcados con * son obligatorios.")
            else:
                payload = {
                    "license_number": new_license,
                    "first_name": new_first,
                    "last_name": new_last,
                    "email": new_email,
                    "password": new_pass, # Campo obligatorio para M6
                    "phone": new_phone,
                    "specialization": new_spec,
                    "hire_date": new_hire.isoformat(),
                    "is_active": new_active,
                    "consultation_fee": new_fee,
                    "rating": 0.0
                }
                
                # Usamos el endpoint /sign-up que creamos para registrar usuarios
                if api_request("POST", "/sign-up", data=payload):
                    st.success(f"¡Dr. {new_last} registrado exitosamente!")
                    st.cache_data.clear()
                    st.rerun()

# --- TAB 3: GESTIÓN ---
with tab_manage:
    st.subheader("Editar o Eliminar")
    
    if vets_list:
        selected_vet_key = st.selectbox("Selecciona un Médico:", options=list(vet_options.keys()))
        
        if selected_vet_key:
            vet_id = vet_options[selected_vet_key]
            current_vet = next((v for v in vets_list if v['veterinarian_id'] == vet_id), None)
            
            if current_vet:
                # Panel de Métricas
                if 'total_appointments' in current_vet:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Citas Totales", current_vet.get('total_appointments', 0))
                    m2.metric("Rating", f"{current_vet.get('rating', 0.0)} ⭐")
                    m3.metric("Tarifa", f"${current_vet.get('consultation_fee', 0.0)}")
                    st.divider()

                with st.form("edit_vet_form"):
                    st.markdown("#### ✏️ Editar Datos")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_email = st.text_input("Email", value=current_vet['email'])
                        edit_phone = st.text_input("Teléfono", value=current_vet.get('phone', ''))
                        edit_spec = st.text_input("Especialización", value=current_vet.get('specialization', ''))
                    
                    with ec2:
                        val_fee = float(current_vet.get('consultation_fee', 0.0)) if current_vet.get('consultation_fee') else 0.0
                        edit_fee = st.number_input("Tarifa ($)", value=val_fee, min_value=0.0)
                        edit_active = st.checkbox("¿Está Activo?", value=current_vet['is_active'])
                    
                    submitted_update = st.form_submit_button("Guardar Cambios")
                    
                    if submitted_update:
                        update_data = {
                            "email": edit_email, "phone": edit_phone,
                            "specialization": edit_spec, "is_active": edit_active,
                            "consultation_fee": edit_fee
                        }
                        if api_request("PUT", f"/veterinarians/{vet_id}", data=update_data):
                            st.success("Datos actualizados.")
                            st.cache_data.clear()
                            st.rerun()

                with st.expander("🚨 Zona de Peligro"):
                    if st.button(f"Eliminar al Dr. {current_vet['last_name']}", type="primary"):
                        if api_request("DELETE", f"/veterinarians/{vet_id}"):
                            st.success("Veterinario eliminado.")
                            st.cache_data.clear()
                            st.rerun()

# Botón flotante
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")