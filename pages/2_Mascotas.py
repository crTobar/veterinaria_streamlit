import streamlit as st
import pandas as pd
import requests

# --- 1. Protección de la Página (Auth) ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión de Mascotas", page_icon="🐶", layout="wide")
API_URL = "http://127.0.0.1:8000"

# --- 3. Función de Carga de Datos ---
@st.cache_data(ttl=5) # Cache corto para que se sienta rápido pero actualizado
def get_data(endpoint):
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    try:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return None

# --- 4. Interfaz Principal ---
st.title("🐶 Gestión de Pacientes (Mascotas)")

# --- Cargar Lista de Mascotas ---
pets_list = get_data("/pets/")

if pets_list:
    # --- BARRAS DE BÚSQUEDA Y FILTRO ---
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        search_term = st.text_input("🔍 Buscar por Nombre o ID:", placeholder="Escribe aquí...")
    
    with col_filter:
        species_filter = st.selectbox("Filtrar por Especie", ["Todas", "dog", "cat", "bird", "rabbit", "other"])

    # --- Lógica de Filtrado ---
    df_pets = pd.DataFrame(pets_list)
    
    # Preparar datos para visualización (Flattening)
    # Extraemos el nombre del dueño para que la tabla sea legible
    df_pets['owner_name'] = df_pets['owner'].apply(lambda x: f"{x['first_name']} {x['last_name']}")
    df_pets['owner_email'] = df_pets['owner'].apply(lambda x: x['email'])
    
    # Filtrar por texto
    if search_term:
        df_pets = df_pets[
            df_pets['name'].astype(str).str.contains(search_term, case=False) | 
            df_pets['pet_id'].astype(str).str.contains(search_term)
        ]
    
    # Filtrar por especie
    if species_filter != "Todas":
        df_pets = df_pets[df_pets['species'] == species_filter]

    # --- MOSTRAR TABLA PRINCIPAL ---
    st.subheader("Listado de Pacientes")
    
    # Definir columnas visibles y amigables
    cols_to_show = ['pet_id', 'name', 'species', 'breed', 'owner_name', 'owner_email']
    
    # Añadir columnas M5 si existen (para que funcione en ambas versiones)
    if 'visit_count' in df_pets.columns:
        cols_to_show.append('visit_count')
        cols_to_show.append('last_visit_date')

    st.dataframe(
        df_pets[cols_to_show].set_index('pet_id'),
        column_config={
            "name": "Nombre",
            "species": "Especie",
            "breed": "Raza",
            "owner_name": "Dueño",
            "visit_count": "Visitas Totales",
            "last_visit_date": "Última Visita"
        },
        width='stretch'
    )
    
    st.divider()

    # --- SECCIÓN DE DETALLES ---
    st.header("📋 Expediente Detallado")
    
    # Crear una lista de opciones para el selectbox: "ID - Nombre (Dueño)"
    pet_options = {f"{p['pet_id']} - {p['name']} ({p['owner']['first_name']})": p['pet_id'] for p in pets_list}
    
    selected_option = st.selectbox("Selecciona una mascota para ver su expediente completo:", options=list(pet_options.keys()))
    
    if selected_option:
        selected_pet_id = pet_options[selected_option]
        
        # Cargar datos específicos de la mascota seleccionada
        # (Usamos endpoints específicos para traer detalles frescos)
        
        # 1. Detalles básicos (ya los tenemos, pero podemos pedir frescos si quieres)
        pet_detail = next((p for p in pets_list if p['pet_id'] == selected_pet_id), None)
        
        # 2. Historial Médico (M1)
        medical_history = get_data(f"/pets/{selected_pet_id}/medical-history")
        
        # 3. Vacunas (M2)
        vaccinations = get_data(f"/pets/{selected_pet_id}/vaccinations")
        
        # --- MOSTRAR DETALLES EN PESTAÑAS ---
        tab_info, tab_medical, tab_vaccines = st.tabs(["ℹ️ Información General", "🩺 Historial Médico", "💉 Vacunación"])
        
        with tab_info:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Nombre:** {pet_detail['name']}")
                st.markdown(f"**Especie:** {pet_detail['species']}")
                st.markdown(f"**Raza:** {pet_detail.get('breed', 'N/A')}")
                st.markdown(f"**Peso:** {pet_detail.get('weight', 'N/A')} kg")
            with c2:
                st.markdown("### Datos del Dueño")
                owner = pet_detail['owner']
                st.markdown(f"**Nombre:** {owner['first_name']} {owner['last_name']}")
                st.markdown(f"**Email:** {owner['email']}")
                st.markdown(f"**Teléfono:** {owner.get('phone', 'N/A')}")
                st.markdown(f"**Dirección:** {owner.get('address', 'N/A')}")
                
                # Datos M3 (si existen)
                if 'emergency_contact' in owner:
                    st.info(f"🚨 **Emergencia:** {owner['emergency_contact']}")

        with tab_medical:
            st.subheader("Historial de Consultas")
            if medical_history:
                for record in medical_history:
                    with st.expander(f"Consulta del {record['created_at'][:10]} - {record['diagnosis'][:30]}..."):
                        st.markdown(f"**Diagnóstico:** {record['diagnosis']}")
                        st.markdown(f"**Tratamiento:** {record['treatment']}")
                        if record.get('prescription'):
                            st.markdown(f"**Receta:** {record['prescription']}")
                        if record.get('follow_up_required'):
                            st.warning("⚠️ Requiere seguimiento")
            else:
                st.info("No hay historial médico registrado para este paciente.")

        with tab_vaccines:
            st.subheader("Registro de Vacunación")
            if vaccinations:
                df_vacs = pd.DataFrame(vaccinations)
                
                # Aplanar datos de la vacuna para mostrar el nombre
                df_vacs['vaccine_name'] = df_vacs['vaccine'].apply(lambda x: x['name'])
                df_vacs['vet_name'] = df_vacs['veterinarian'].apply(lambda x: f"Dr. {x['last_name']}")
                
                st.dataframe(
                    df_vacs[['vaccination_date', 'vaccine_name', 'batch_number', 'next_dose_date', 'vet_name']],
                    column_config={
                        "vaccination_date": "Fecha Aplicación",
                        "vaccine_name": "Vacuna",
                        "batch_number": "Lote",
                        "next_dose_date": "Próxima Dosis",
                        "vet_name": "Veterinario"
                    },
                    width='stretch',
                    hide_index=True
                )
            else:
                st.info("No se han registrado vacunas para este paciente.")

else:
    st.info("No hay mascotas registradas en el sistema.")

# Botón flotante para volver
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")