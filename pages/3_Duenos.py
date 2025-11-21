import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. Protección de la Página (Auth) ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión de Dueños", page_icon="👤", layout="wide")
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
        return None

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
st.title("👤 Gestión de Clientes (Dueños)")

# Cargar datos de dueños
owners_list = get_data("/owners/")

if owners_list:
    
    # Preparar datos para facilitar su uso (Diccionario ID -> Nombre)
    owner_options = {f"{o['owner_id']} - {o['first_name']} {o['last_name']}": o['owner_id'] for o in owners_list}
    
    # --- PESTAÑAS DE ACCIÓN ---
    tab_list, tab_details, tab_add_pet, tab_new_owner = st.tabs([
        "📋 Listado y Búsqueda", 
        "🔍 Detalles y Mascotas", 
        "➕ Agregar Mascota a Cliente", 
        "🆕 Nuevo Cliente"
    ])

    # --- TAB 1: LISTADO GENERAL ---
    with tab_list:
        # Barra de búsqueda
        search_term = st.text_input("🔍 Buscar Dueño (Nombre, Apellido o ID):", placeholder="Escribe para filtrar...")
        
        # Procesar datos para la tabla
        owner_data_processed = []
        for o in owners_list:
            # Calculamos cuántas mascotas tiene contando la lista 'pets' que viene en el JSON
            num_pets = len(o.get('pets', []))
            pets_names = ", ".join([p['name'] for p in o.get('pets', [])])
            
            owner_data_processed.append({
                "ID": o['owner_id'],
                "Nombre": o['first_name'],
                "Apellido": o['last_name'],
                "Email": o['email'],
                "Teléfono": o.get('phone', 'N/A'),
                "Num. Mascotas": num_pets, # <--- Aquí está el conteo
                "Nombres Mascotas": pets_names
            })
        
        df_owners = pd.DataFrame(owner_data_processed)
        
        # Filtrar
        if search_term:
            df_owners = df_owners[
                df_owners['Nombre'].str.contains(search_term, case=False) |
                df_owners['Apellido'].str.contains(search_term, case=False) |
                df_owners['ID'].astype(str).str.contains(search_term)
            ]
            
        st.dataframe(
            df_owners.set_index("ID"), 
            width='stretch',
            column_config={
                "Num. Mascotas": st.column_config.NumberColumn(
                    "Mascotas",
                    help="Cantidad de mascotas registradas",
                    format="%d 🐾"
                )
            }
        )

    # --- TAB 2: DETALLES (Ver las mascotas de un dueño específico) ---
    with tab_details:
        st.subheader("Expediente del Cliente")
        col_sel, col_void = st.columns([1, 1])
        with col_sel:
            selected_owner_key = st.selectbox("Selecciona un Dueño:", options=list(owner_options.keys()), key="sel_details")
        
        if selected_owner_key:
            owner_id = owner_options[selected_owner_key]
            # Buscar el objeto dueño completo en la lista cargada
            owner_detail = next((o for o in owners_list if o['owner_id'] == owner_id), None)
            
            if owner_detail:
                st.markdown(f"### 👤 {owner_detail['first_name']} {owner_detail['last_name']}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Email:** {owner_detail['email']}")
                c2.markdown(f"**Teléfono:** {owner_detail.get('phone', 'N/A')}")
                c3.markdown(f"**Dirección:** {owner_detail.get('address', 'N/A')}")
                
                st.divider()
                st.markdown(f"### 🐾 Mascotas de {owner_detail['first_name']} ({len(owner_detail['pets'])})")
                
                if owner_detail['pets']:
                    # Convertir la lista de mascotas a DataFrame
                    df_pets = pd.DataFrame(owner_detail['pets'])
                    st.dataframe(
                        df_pets[['pet_id', 'name', 'species']].set_index('pet_id'),
                        width='stretch',
                        column_config={
                            "name": "Nombre",
                            "species": "Especie"
                        }
                    )
                else:
                    st.info("Este dueño no tiene mascotas registradas actualmente.")

    # --- TAB 3: AGREGAR MASCOTA A DUEÑO EXISTENTE ---
    with tab_add_pet:
        st.subheader("Añadir nueva mascota a un cliente existente")
        
        with st.form("add_pet_to_existing_form"):
            # 1. Seleccionar el dueño existente
            selected_owner_for_add = st.selectbox("Selecciona al Dueño:", options=list(owner_options.keys()), key="sel_add_pet")
            
            st.markdown("---")
            st.write("**Datos de la Nueva Mascota:**")
            
            # 2. Datos de la mascota
            c1, c2 = st.columns(2)
            with c1:
                p_name = st.text_input("Nombre Mascota*")
                p_species = st.selectbox("Especie*", ['dog', 'cat', 'bird', 'rabbit', 'other'])
                p_breed = st.text_input("Raza")
                p_microchip = st.text_input("Microchip (M3)")
            with c2:
                p_birth = st.date_input("Fecha Nacimiento", value=None)
                p_weight = st.number_input("Peso (kg)", min_value=0.1, value=1.0)
                p_neutered = st.checkbox("Esterilizado", False)
                p_blood = st.text_input("Tipo Sangre", max_chars=10)
                
            submitted_add = st.form_submit_button("Guardar Nueva Mascota")
            
            if submitted_add:
                if not p_name:
                    st.error("El nombre de la mascota es obligatorio.")
                else:
                    # Obtener el ID del dueño seleccionado
                    owner_id_to_add = owner_options[selected_owner_for_add]
                    
                    pet_data = {
                        "name": p_name,
                        "species": p_species,
                        "breed": p_breed,
                        "birth_date": p_birth.isoformat() if p_birth else None,
                        "weight": p_weight,
                        "owner_id": owner_id_to_add, # <--- AQUÍ ASOCIAMOS AL DUEÑO EXISTENTE
                        "microchip_number": p_microchip,
                        "is_neutered": p_neutered,
                        "blood_type": p_blood
                    }
                    
                    response = api_request("POST", "/pets/", data=pet_data)
                    if response:
                        st.success(f"¡Mascota '{p_name}' añadida correctamente al dueño!")
                        st.rerun()

    # --- TAB 4: NUEVO CLIENTE (Lógica combinada) ---
    with tab_new_owner:
        st.subheader("Registrar Nuevo Cliente (y su primera mascota)")
        st.info("Para dar de alta un cliente nuevo, es obligatorio registrar al menos una mascota.")
        
        with st.form("create_new_owner_full"):
            # Formulario combinado (similar al del menú principal)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Datos del Dueño**")
                n_first = st.text_input("Nombre*")
                n_last = st.text_input("Apellido*")
                n_email = st.text_input("Email*")
                n_phone = st.text_input("Teléfono")
                n_address = st.text_input("Dirección")
                n_emer = st.text_input("Contacto Emergencia")
                n_pay = st.selectbox("Pago Preferido", [None, 'cash', 'credit', 'debit', 'insurance'])
            
            with c2:
                st.markdown("**Datos de la Primera Mascota**")
                np_name = st.text_input("Nombre Mascota*")
                np_species = st.selectbox("Especie", ['dog', 'cat', 'bird', 'rabbit', 'other'])
                np_breed = st.text_input("Raza")
                np_birth = st.date_input("Nacimiento", value=None)
                np_weight = st.number_input("Peso", 0.1, 100.0, 5.0)
            
            submit_new_client = st.form_submit_button("Registrar Cliente")
            
            if submit_new_client:
                if not n_first or not n_last or not n_email or not np_name:
                    st.error("Faltan datos obligatorios.")
                else:
                    # 1. Crear Dueño
                    owner_payload = {
                        "first_name": n_first, "last_name": n_last, "email": n_email,
                        "phone": n_phone, "address": n_address,
                        "emergency_contact": n_emer, "preferred_payment_method": n_pay
                    }
                    res_owner = api_request("POST", "/owners/", data=owner_payload)
                    
                    if res_owner:
                        # 2. Crear Mascota con el ID del dueño
                        pet_payload = {
                            "name": np_name, "species": np_species, "breed": np_breed,
                            "birth_date": np_birth.isoformat() if np_birth else None,
                            "weight": np_weight, "owner_id": res_owner['owner_id']
                        }
                        res_pet = api_request("POST", "/pets/", data=pet_payload)
                        
                        if res_pet:
                            st.success(f"Cliente {n_first} y mascota {np_name} registrados con éxito.")
                            st.rerun()

else:
    st.info("No hay dueños registrados o no se pudo conectar con la API.")

# Botón flotante para volver
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")