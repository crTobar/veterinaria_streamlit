import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, time

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Clínica Veterinaria",
    page_icon="🐾",
    layout="wide"
)

# URL base de tu API de FastAPI (asegúrate de que esté corriendo)
API_URL = "http://127.0.0.1:8000"

# --- Funciones de Utilidad (Login/Logout/API) ---

@st.cache_data(ttl=10) # Cachear los datos por 10 segundos
def get_protected_data(endpoint: str):
    """
    Función genérica para peticiones GET a endpoints protegidos.
    Usa el token guardado en st.session_state.
    """
    if 'auth_token' not in st.session_state or st.session_state['auth_token'] is None:
        st.error("No estás autenticado. Por favor, inicia sesión.")
        st.session_state['logged_in'] = False # Forzar logout si el token desaparece
        return None
    
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    
    try:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if response.status_code == 401:
            st.error("Tu sesión ha expirado. Por favor, inicia sesión de nuevo.")
            st.session_state['logged_in'] = False
            st.session_state['auth_token'] = None
            st.rerun()
        else:
            st.error(f"Error al obtener datos ({endpoint}): {e}")
        return None

def api_request(method: str, endpoint: str, data: dict = None, params: dict = None):
    """
    Función genérica para peticiones POST, PUT, DELETE.
    """
    if 'auth_token' not in st.session_state or st.session_state['auth_token'] is None:
        st.error("No estás autenticado. Por favor, inicia sesión.")
        return None
    
    headers = {"Authorization": f"Bearer {st.session_state['auth_token']}"}
    url = f"{API_URL}{endpoint}"

    try:
        response = None
        if method == "POST":
            response = requests.post(url, headers=headers, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, params=params)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        
        response.raise_for_status()
        
        # DELETE puede no devolver JSON (204 No Content), lo cual está bien
        if response.status_code != 204:
            return response.json()
        return True # Éxito para DELETE
        
    except requests.exceptions.RequestException as e:
        error_detail = f"Error: {e}"
        try:
            error_detail = response.json().get('detail', error_detail)
        except:
            pass # Mantener el error original
        st.error(f"Error al {method} en ({endpoint}): {error_detail}")
        return None

def login_user(email, password):
    """Intenta iniciar sesión en la API."""
    try:
        login_data = {'username': email, 'password': password}
        response = requests.post(f"{API_URL}/login", data=login_data)
        response.raise_for_status()
        token_data = response.json()
        return token_data['access_token']
    except requests.exceptions.RequestException:
        try:
            error_detail = response.json().get('detail', "Error desconocido")
        except:
            error_detail = "Error de conexión. ¿La API está corriendo?"
        st.error(f"Error al iniciar sesión: {error_detail}")
        return None

def show_logout_button():
    """Muestra un botón de logout en la esquina superior derecha."""
    with st.container():
        st.write("") # Espacio
        col1, col2, col3 = st.columns([.8, .1, .1])
        with col3:
            if st.button("Cerrar Sesión 🔒"):
                # Limpiar todo el estado de sesión
                for key in st.session_state.keys():
                    del st.session_state[key]
                st.rerun()

# --- Lógica de Estado de Sesión (El "Guardia") ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['auth_token'] = None

# --- Página de Login (Si no está logueado) ---
if not st.session_state['logged_in']:
    st.title("Bienvenido a la Clínica Veterinaria 🐾")
    st.subheader("Por favor, inicia sesión para continuar")

    with st.form("login_form"):
        email = st.text_input("Email (Veterinario)")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Iniciar Sesión")

        if submitted:
            if not email or not password:
                st.warning("Por favor, ingresa email y contraseña.")
            else:
                with st.spinner("Iniciando sesión..."):
                    token = login_user(email, password)
                    
                    if token:
                        st.session_state['logged_in'] = True
                        st.session_state['auth_token'] = token
                        st.success("¡Inicio de sesión exitoso!")
                        st.rerun()
    
    st.divider()
    with st.expander("¿Olvidaste tu contraseña?"):
        st.subheader("Recuperar Contraseña")
        recovery_email = st.text_input("Ingresa tu email de veterinario")
        if st.button("Recuperar"):
            if not recovery_email:
                st.warning("Por favor, ingresa un email.")
            else:
                try:
                    response = requests.post(f"{API_URL}/recover-password", json={"email": recovery_email})
                    response.raise_for_status()
                    st.success("¡Hecho! Se generó una nueva contraseña. Revisa la consola de tu servidor de API (Uvicorn) para verla.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Error: {e.json().get('detail', str(e))}")

# --- Aplicación Principal (Si SÍ está logueado) ---
else:
    show_logout_button()
    
    st.title("🐾 Dashboard de Gestión de la Clínica")
    
    # --- PESTAÑAS (TABS) PARA CADA RECURSO ---
    tab_vets, tab_owners, tab_pets, tab_appts, tab_vaccines, tab_vacc_records, tab_invoices = st.tabs(
        ["Veterinarios", "Dueños", "Mascotas", "Citas", "Vacunas", "Registros Vac.", "Facturas"]
    )

    # --- Pestaña de Veterinarios ---
    with tab_vets:
        st.header("Gestión de Veterinarios")
        tab_ver_vets, tab_crear_vet = st.tabs(["Ver Veterinarios", "Crear Nuevo Veterinario"])
        
        with tab_ver_vets:
            st.subheader("Lista de Veterinarios")
            vet_data = get_protected_data("/veterinarians/")
            if vet_data:
                df_vets = pd.DataFrame(vet_data)
                display_cols = ["veterinarian_id", "first_name", "last_name", "email", "phone", "specialization", "is_active"]
                if 'consultation_fee' in df_vets.columns:
                    display_cols.extend(["consultation_fee", "rating", "total_appointments"])
                
                # CORRECCIÓN: 'use_container_width' -> 'width'
                st.dataframe(df_vets[display_cols].set_index("veterinarian_id"), width='stretch')

        with tab_crear_vet:
            st.subheader("Crear Nuevo Veterinario (/sign-up)")
            with st.form("new_vet_form"):
                c1, c2 = st.columns(2)
                with c1:
                    vet_first_name = st.text_input("Nombre*")
                    vet_email = st.text_input("Email*")
                    vet_license = st.text_input("N° de Licencia*")
                    vet_specialization = st.text_input("Especialización")
                    vet_fee = st.number_input("Tarifa de Consulta (M5)", min_value=0.0, format="%.2f")
                with c2:
                    vet_last_name = st.text_input("Apellido*")
                    vet_phone = st.text_input("Teléfono")
                    vet_hire_date = st.date_input("Fecha de Contratación", datetime.now())
                    vet_password = st.text_input("Contraseña (para su login)*", type="password")
                    vet_is_active = st.checkbox("Está Activo", True)

                vet_submitted = st.form_submit_button("Registrar Veterinario")
                
                if vet_submitted:
                    vet_data = {
                        "license_number": vet_license, "first_name": vet_first_name,
                        "last_name": vet_last_name, "email": vet_email, "password": vet_password,
                        "phone": vet_phone, "specialization": vet_specialization,
                        "hire_date": vet_hire_date.isoformat(), "is_active": vet_is_active,
                        "consultation_fee": vet_fee, "rating": 0
                    }
                    # Usamos la función genérica (no protegida para sign-up)
                    result = requests.post(f"{API_URL}/sign-up", json=vet_data) 
                    if result.status_code == 201:
                        st.success(f"¡Veterinario '{result.json()['first_name']}' registrado!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result.json().get('detail')}")

    # --- Pestaña de Dueños ---
    with tab_owners:
        st.header("Gestión de Dueños y Mascotas")
        st.subheader("Registrar Nuevo Dueño (y su primera mascota)")
        
        with st.form("new_owner_and_pet_form"):
            st.warning("No se puede crear un Dueño sin al menos una Mascota.", icon="⚠️")
            c1, c2 = st.columns(2)
            with c1:
                st.info("Datos del Dueño (M3)")
                owner_first_name = st.text_input("Nombre (Dueño)*")
                owner_last_name = st.text_input("Apellido (Dueño)*")
                owner_email = st.text_input("Email (Dueño)*")
                owner_phone = st.text_input("Teléfono (Dueño)")
                owner_address = st.text_area("Dirección (Dueño)")
                owner_emergency = st.text_input("Contacto Emergencia (Dueño)")
                owner_payment = st.selectbox("Método de Pago (Dueño)", [None, 'cash', 'credit', 'debit', 'insurance'], index=0)
            with c2:
                st.info("Datos de la Primera Mascota (M3)")
                pet_name = st.text_input("Nombre (Mascota)*")
                pet_species = st.selectbox("Especie*", ['dog', 'cat', 'bird', 'rabbit', 'other'])
                pet_breed = st.text_input("Raza")
                pet_birth_date = st.date_input("Fecha Nacimiento (Mascota)", None)
                pet_weight = st.number_input("Peso (kg)", min_value=0.1, value=1.0, format="%.2f")
                pet_microchip = st.text_input("Microchip (Mascota)")
                pet_neutered = st.checkbox("Esterilizado (Mascota)", False)
                pet_blood_type = st.text_input("Tipo de Sangre (Mascota)", max_chars=10)

            owner_pet_submitted = st.form_submit_button("Registrar Dueño y Mascota")
            
            if owner_pet_submitted:
                if not owner_first_name or not owner_last_name or not owner_email or not pet_name:
                    st.error("Nombre, Apellido, Email del Dueño y Nombre de la Mascota son obligatorios.")
                else:
                    owner_data = {
                        "first_name": owner_first_name, "last_name": owner_last_name,
                        "email": owner_email, "phone": owner_phone, "address": owner_address,
                        "emergency_contact": owner_emergency, "preferred_payment_method": owner_payment
                    }
                    owner_response = api_request("POST", "/owners/", data=owner_data)
                    
                    if owner_response:
                        new_owner = owner_response
                        st.success(f"Dueño '{new_owner['first_name']}' creado con ID {new_owner['owner_id']}.")
                        pet_data = {
                            "name": pet_name, "species": pet_species, "breed": pet_breed,
                            "birth_date": pet_birth_date.isoformat() if pet_birth_date else None,
                            "weight": pet_weight,
                            "owner_id": new_owner['owner_id'],
                            "microchip_number": pet_microchip,
                            "is_neutered": pet_neutered,
                            "blood_type": pet_blood_type
                        }
                        pet_response = api_request("POST", "/pets/", data=pet_data)
                        if pet_response:
                            st.success(f"Mascota '{pet_name}' creada y asociada al dueño!")
                            st.rerun()

        st.divider()
        st.subheader("Ver Todos los Dueños")
        owners_data = get_protected_data("/owners/")
        if owners_data:
            # CORRECCIÓN: 'width'
            st.dataframe(pd.DataFrame(owners_data), width='stretch')

    # --- Pestaña de Mascotas ---
    with tab_pets:
        st.header("Gestión de Mascotas")
        st.write("Aquí puedes ver y actualizar mascotas existentes.")
        pets_data = get_protected_data("/pets/")
        if pets_data:
            df_pets = pd.DataFrame(pets_data)
            df_pets['owner_name'] = df_pets['owner'].apply(lambda x: f"{x.get('first_name','')} {x.get('last_name','')}")
            columns_to_show = ["pet_id", "name", "species", "breed", "owner_name"]
            if pets_data and 'visit_count' in pets_data[0]:
                columns_to_show.extend(["visit_count", "last_visit_date"])
            if pets_data and 'microchip_number' in pets_data[0]:
                columns_to_show.extend(["microchip_number", "is_neutered"])
            
            # CORRECCIÓN: 'width'
            st.dataframe(df_pets[columns_to_show].set_index("pet_id"), width='stretch')

    # --- Pestaña de Citas ---
    with tab_appts:
        st.header("Gestión de Citas")
        st.subheader("Crear Cita (Normal o Emergencia)")
        
        with st.form("new_appointment_form"):
            st.info("Para una emergencia, deja el 'ID de Mascota' en 0 o vacío.")
            c1, c2 = st.columns(2)
            with c1:
                appt_pet_id = st.number_input("ID de Mascota (Opcional)", min_value=0, value=0, step=1)
                appt_vet_id = st.number_input("ID de Veterinario*", min_value=1, step=1)
                
                # --- CORRECCIÓN: Usar st.date_input y st.time_input ---
                appt_date_val = st.date_input("Fecha de la Cita*", value=datetime.now().date())
                appt_time_val = st.time_input("Hora de la Cita*", value=datetime.now().time())
                # ---------------------------------------------------
                
            with c2:
                appt_reason = st.text_area("Razón de la Cita")
                appt_notes = st.text_area("Notas de Emergencia (si no hay mascota)")

            appt_submitted = st.form_submit_button("Crear Cita")
            
            if appt_submitted:
                try:
                    combined_datetime = datetime.combine(appt_date_val, appt_time_val)
                    
                    appt_data = {
                        "pet_id": appt_pet_id if appt_pet_id > 0 else None,
                        "veterinarian_id": appt_vet_id,
                        "appointment_date": combined_datetime.isoformat(),
                        "reason": appt_reason,
                        "status": "scheduled",
                        "notes": appt_notes
                    }
                    
                    response = api_request("POST", "/appointments/", data=appt_data)
                    if response:
                        st.success("¡Cita creada exitosamente!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar la cita: {e}")

        st.divider()
        st.subheader("Ver Todas las Citas")
        appts_data = get_protected_data("/appointments/")
        if appts_data:
            # CORRECCIÓN: 'width'
            st.dataframe(pd.DataFrame(appts_data), width='stretch')

    # --- Pestaña de Vacunas ---
    with tab_vaccines:
        st.header("Gestión de Vacunas (M2)")
        
        with st.form("new_vaccine_form"):
            st.subheader("Añadir Nuevo Tipo de Vacuna")
            c1, c2, c3 = st.columns(3)
            with c1:
                vac_name = st.text_input("Nombre de la Vacuna*")
            with c2:
                vac_manufacturer = st.text_input("Fabricante")
            with c3:
                vac_species = st.text_input("Especies Aplicables (ej. dog, cat)")
            
            vac_submitted = st.form_submit_button("Crear Vacuna")
            if vac_submitted:
                if not vac_name:
                    st.error("El nombre es obligatorio.")
                else:
                    vac_data = {
                        "name": vac_name,
                        "manufacturer": vac_manufacturer,
                        "species_applicable": vac_species
                    }
                    response = api_request("POST", "/vaccines/", data=vac_data)
                    if response:
                        st.success(f"Vacuna '{response['name']}' creada.")
                        st.rerun()
        
        st.divider()
        st.subheader("Catálogo de Vacunas")
        vaccines_data = get_protected_data("/vaccines/")
        if vaccines_data:
            st.dataframe(pd.DataFrame(vaccines_data).set_index("vaccine_id"), width='stretch')

    # --- Pestaña de Registros de Vacunación ---
    with tab_vacc_records:
        st.header("Gestión de Registros de Vacunación (M2)")
        
        with st.form("new_vacc_record_form"):
            st.subheader("Registrar Vacuna Aplicada")
            c1, c2, c3 = st.columns(3)
            with c1:
                rec_pet_id = st.number_input("ID de Mascota*", min_value=1, step=1)
                rec_vaccine_id = st.number_input("ID de Vacuna*", min_value=1, step=1)
                rec_vet_id = st.number_input("ID de Veterinario*", min_value=1, step=1)
            with c2:
                rec_date = st.date_input("Fecha de Vacunación*", value=datetime.now())
                rec_next_date = st.date_input("Próxima Dosis (Opcional)", value=None)
                rec_batch = st.text_input("Número de Lote", max_chars=50)

            rec_submitted = st.form_submit_button("Registrar Aplicación")
            if rec_submitted:
                rec_data = {
                    "pet_id": rec_pet_id,
                    "vaccine_id": rec_vaccine_id,
                    "veterinarian_id": rec_vet_id,
                    "vaccination_date": rec_date.isoformat(),
                    "next_dose_date": rec_next_date.isoformat() if rec_next_date else None,
                    "batch_number": rec_batch
                }
                response = api_request("POST", "/vaccination-records/", data=rec_data)
                if response:
                    st.success(f"Registro creado con ID {response['vaccination_id']} para la mascota {response['pet']['name']}.")
                    st.rerun()

        st.divider()
        st.subheader("Historial de Registros de Vacunación")
        vacc_records_data = get_protected_data("/vaccination-records/")
        if vacc_records_data:
            st.dataframe(pd.DataFrame(vacc_records_data), width='stretch')

    # --- Pestaña de Facturas ---
    with tab_invoices:
        st.header("Gestión de Facturas (M4)")
        st.subheader("Facturas Pendientes de Pago")
        
        pending_invoices_data = get_protected_data("/invoices/pending")
        if pending_invoices_data:
            df_pending = pd.DataFrame(pending_invoices_data)
            
            if not df_pending.empty:
                # Seleccionar una factura para pagar
                invoice_ids = df_pending['invoice_id'].tolist()
                invoice_to_pay = st.selectbox("Selecciona una Factura para Pagar", options=invoice_ids)
                
                if st.button("Marcar como Pagada"):
                    if invoice_to_pay:
                        with st.spinner(f"Pagando factura {invoice_to_pay}..."):
                            response = api_request("POST", f"/invoices/{invoice_to_pay}/pay")
                            if response:
                                st.success(f"¡Factura {response['invoice_number']} marcada como 'paid'!")
                                st.rerun()
            else:
                st.info("No hay facturas pendientes.")

        st.divider()
        st.subheader("Todas las Facturas")
        all_invoices_data = get_protected_data("/invoices/")
        if all_invoices_data:
            st.dataframe(pd.DataFrame(all_invoices_data).set_index("invoice_id"), width='stretch')