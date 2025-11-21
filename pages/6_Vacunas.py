import streamlit as st
import pandas as pd
import requests

# --- 1. Protección de la Página (Auth) ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión de Vacunas", page_icon="💉", layout="wide")
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
st.title("💉 Catálogo de Biológicos (Vacunas)")

# Cargar datos
vaccines_list = get_data("/vaccines/")

# --- PESTAÑAS ---
tab_catalog, tab_create = st.tabs(["📋 Catálogo y Edición", "➕ Registrar Nueva Vacuna"])

# --- TAB 1: CATÁLOGO Y EDICIÓN ---
with tab_catalog:
    st.subheader("Inventario de Vacunas Disponibles")
    
    if vaccines_list:
        # 1. Mostrar Tabla
        df_vaccines = pd.DataFrame(vaccines_list)
        
        st.dataframe(
            df_vaccines.set_index("vaccine_id"),
            column_config={
                "name": "Nombre Comercial",
                "manufacturer": "Laboratorio / Fabricante",
                "species_applicable": st.column_config.TextColumn("Especies", help="Especies para las que es válida")
            },
            width='stretch'
        )
        
        st.divider()
        st.subheader("✏️ Modificar o Eliminar Vacuna")
        
        # Selector para editar
        vac_options = {f"{v['vaccine_id']} - {v['name']}": v['vaccine_id'] for v in vaccines_list}
        selected_vac_key = st.selectbox("Selecciona una vacuna para editar:", options=list(vac_options.keys()))
        
        if selected_vac_key:
            vac_id = vac_options[selected_vac_key]
            current_vac = next((v for v in vaccines_list if v['vaccine_id'] == vac_id), None)
            
            if current_vac:
                with st.form("edit_vaccine_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        new_name = st.text_input("Nombre", value=current_vac['name'])
                        new_manuf = st.text_input("Fabricante", value=current_vac.get('manufacturer', ''))
                    
                    with c2:
                        # Convertir string "dog,cat" a lista ["dog", "cat"] para el multiselect
                        current_species_str = current_vac.get('species_applicable', '')
                        default_species = current_species_str.split(',') if current_species_str else []
                        # Filtrar para asegurar que sean opciones validas del multiselect
                        valid_options = ['dog', 'cat', 'bird', 'rabbit', 'other']
                        default_species = [s for s in default_species if s in valid_options]
                        
                        new_species_list = st.multiselect("Especies Aplicables", valid_options, default=default_species)
                    
                    c_save, c_del = st.columns([1, 1])
                    with c_save:
                        submit_update = st.form_submit_button("💾 Guardar Cambios")
                    with c_del:
                        submit_delete = st.form_submit_button("🗑️ Eliminar Vacuna", type="primary")
                    
                    if submit_update:
                        # Convertir lista de vuelta a string "dog,cat"
                        species_str = ",".join(new_species_list)
                        payload = {
                            "name": new_name,
                            "manufacturer": new_manuf,
                            "species_applicable": species_str
                        }
                        if api_request("PUT", f"/vaccines/{vac_id}", data=payload):
                            st.success("Vacuna actualizada correctamente.")
                            st.cache_data.clear()
                            st.rerun()
                    
                    if submit_delete:
                        if api_request("DELETE", f"/vaccines/{vac_id}"):
                            st.success("Vacuna eliminada del catálogo.")
                            st.cache_data.clear()
                            st.rerun()

    else:
        st.info("No hay vacunas registradas.")

# --- TAB 2: CREAR ---
with tab_create:
    st.subheader("Registrar Nuevo Tipo de Vacuna")
    
    with st.form("create_vaccine_form"):
        c1, c2 = st.columns(2)
        with c1:
            create_name = st.text_input("Nombre de la Vacuna*")
            create_manuf = st.text_input("Fabricante")
        with c2:
            create_species_list = st.multiselect("Especies Aplicables", ['dog', 'cat', 'bird', 'rabbit', 'other'])
        
        submitted_create = st.form_submit_button("Crear Vacuna")
        
        if submitted_create:
            if not create_name:
                st.error("El nombre es obligatorio.")
            else:
                species_str = ",".join(create_species_list)
                payload = {
                    "name": create_name,
                    "manufacturer": create_manuf,
                    "species_applicable": species_str
                }
                
                if api_request("POST", "/vaccines/", data=payload):
                    st.success(f"Vacuna '{create_name}' creada exitosamente.")
                    st.cache_data.clear()
                    st.rerun()

# Botón flotante
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_🐾_Menu_Principal.py")