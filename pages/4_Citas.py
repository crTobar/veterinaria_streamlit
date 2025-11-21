import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date, time, timedelta

# --- 1. Protección de la Página (Auth) ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.switch_page("app_streamlit.py")

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión de Citas", page_icon="📅", layout="wide")
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
        if response.status_code == 404:
            return []
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
st.title("📅 Gestión de Citas y Emergencias")

# Cargar datos necesarios
appts_list = get_data("/appointments/")
pets_list = get_data("/pets/")
vets_list = get_data("/veterinarians/")

# Mapeos para selectboxes
pet_options = {f"{p['pet_id']} - {p['name']}": p['pet_id'] for p in pets_list} if pets_list else {}
vet_options = {f"{v['veterinarian_id']} - {v['first_name']} {v['last_name']}": v['veterinarian_id'] for v in vets_list} if vets_list else {}

# --- PESTAÑAS ---
tab_list, tab_create, tab_manage = st.tabs(["📋 Calendario y Lista", "➕ Nueva Cita / Emergencia", "✏️ Modificar / Eliminar"])

# --- TAB 1: LISTADO ---
with tab_list:
    st.subheader("Citas Programadas")
    
    if appts_list:
        c1, c2 = st.columns(2)
        with c1:
            filter_date = st.date_input("Filtrar por Fecha", value=None)
        with c2:
            filter_status = st.selectbox("Filtrar por Estado", ["Todos", "scheduled", "completed", "cancelled", "no_show"])

        data_processed = []
        for a in appts_list:
            pet_info = a.get('pet')
            pet_name = pet_info['name'] if pet_info else "🚨 EMERGENCIA (Sin Mascota)"
            vet_name = f"{a['veterinarian']['first_name']} {a['veterinarian']['last_name']}"
            
            dt_obj = datetime.fromisoformat(a['appointment_date'])
            
            if filter_date and dt_obj.date() != filter_date:
                continue
            if filter_status != "Todos" and a['status'] != filter_status:
                continue

            data_processed.append({
                "ID": a['appointment_id'],
                "Fecha": dt_obj.strftime('%Y-%m-%d'),
                "Hora": dt_obj.strftime('%H:%M'),
                "Paciente": pet_name,
                "Veterinario": vet_name,
                "Estado": a['status'],
                "Motivo": a.get('reason', '')
            })
        
        if data_processed:
            st.dataframe(pd.DataFrame(data_processed).set_index("ID"), width='stretch')
        else:
            st.info("No se encontraron citas con esos filtros.")
    else:
        st.info("No hay citas registradas.")

# --- TAB 2: CREAR (CON VALIDACIÓN ACTUALIZADA) ---
with tab_create:
    st.subheader("Agendar Nueva Cita")
    
    with st.form("create_appt_form"):
        is_emergency = st.toggle("🚨 ¿Es una Emergencia? (Paciente no registrado)", value=False)
        
        c1, c2 = st.columns(2)
        with c1:
            if is_emergency:
                st.warning("Modo Emergencia: No se requiere seleccionar mascota.")
                selected_pet_id = None
            else:
                selected_pet_key = st.selectbox("Seleccionar Mascota*", options=list(pet_options.keys()))
                selected_pet_id = pet_options[selected_pet_key] if selected_pet_key else None
            
            selected_vet_key = st.selectbox("Seleccionar Veterinario*", options=list(vet_options.keys()))
            
        with c2:
            new_date = st.date_input("Fecha*", min_value=date.today())
            new_time = st.time_input("Hora*") 
        
        reason = st.text_area("Motivo de la consulta*")
        notes = st.text_area("Notas adicionales")
        
        submitted = st.form_submit_button("Agendar Cita")
        
        if submitted:
            if not selected_vet_key or not reason:
                st.error("Faltan datos obligatorios.")
            elif not is_emergency and not selected_pet_id:
                st.error("Debes seleccionar una mascota.")
            else:
                # 1. Preparar datos
                vet_id = vet_options[selected_vet_key]
                target_start = datetime.combine(new_date, new_time)
                DURATION_MINUTES = 30 
                target_end = target_start + timedelta(minutes=DURATION_MINUTES)
                
                # 2. VALIDACIÓN DE "OVERBOOKING" (Ignorando completadas)
                conflict = False
                conflict_msg = ""
                
                for existing in appts_list:
                    # --- CAMBIO CLAVE AQUÍ ---
                    # Ahora ignoramos también las citas 'completed'
                    if existing['status'] in ['cancelled', 'no_show', 'completed']:
                        continue
                        
                    if existing['veterinarian']['veterinarian_id'] == vet_id:
                        existing_start = datetime.fromisoformat(existing['appointment_date'])
                        existing_end = existing_start + timedelta(minutes=DURATION_MINUTES)
                        
                        if target_start < existing_end and target_end > existing_start:
                            conflict = True
                            time_str = existing_start.strftime('%H:%M')
                            end_str = existing_end.strftime('%H:%M')
                            conflict_msg = f"El veterinario tiene una cita ACTIVA de {time_str} a {end_str}."
                            break
                
                if conflict:
                    st.error(f"🚫 ERROR DE HORARIO: {conflict_msg} Por favor selecciona otra hora.")
                else:
                    payload = {
                        "pet_id": selected_pet_id,
                        "veterinarian_id": vet_id,
                        "appointment_date": target_start.isoformat(),
                        "reason": reason,
                        "status": "scheduled",
                        "notes": notes
                    }
                    
                    res = api_request("POST", "/appointments/", data=payload)
                    if res:
                        st.success("✅ Cita agendada correctamente.")
                        st.cache_data.clear()
                        st.rerun()

# --- TAB 3: GESTIONAR ---
with tab_manage:
    st.subheader("Modificar o Cancelar Citas")
    
    appt_options = {}
    if appts_list:
        for a in appts_list:
            pet_info = a.get('pet')
            pet_str = pet_info['name'] if pet_info else "EMERGENCIA"
            dt_str = datetime.fromisoformat(a['appointment_date']).strftime('%Y-%m-%d %H:%M')
            label = f"ID: {a['appointment_id']} | {dt_str} | {pet_str}"
            appt_options[label] = a['appointment_id']

    selected_appt_label = st.selectbox("Buscar Cita para editar:", options=list(appt_options.keys()))

    if selected_appt_label:
        appt_id = appt_options[selected_appt_label]
        current_appt = next((a for a in appts_list if a['appointment_id'] == appt_id), None)
        
        if current_appt:
            st.info(f"Editando Cita ID: {appt_id}")
            with st.form("edit_appt_form"):
                c1, c2 = st.columns(2)
                with c1:
                    edit_status = st.selectbox("Estado", 
                                             ["scheduled", "completed", "cancelled", "no_show"], 
                                             index=["scheduled", "completed", "cancelled", "no_show"].index(current_appt['status']))
                    edit_notes = st.text_area("Notas", value=current_appt.get('notes', ''))
                with c2:
                    orig_dt = datetime.fromisoformat(current_appt['appointment_date'])
                    st.write(f"📅 Fecha: {orig_dt}")
                    st.write(f"🩺 Vet: {current_appt['veterinarian']['first_name']} {current_appt['veterinarian']['last_name']}")
                
                col_save, col_del = st.columns([1, 1])
                with col_save:
                    submit_update = st.form_submit_button("💾 Guardar Cambios")
                with col_del:
                    submit_delete = st.form_submit_button("🗑️ Eliminar Cita", type="primary")

                if submit_update:
                    payload = {"status": edit_status, "notes": edit_notes}
                    if api_request("PUT", f"/appointments/{appt_id}", data=payload):
                        st.success("Cita actualizada.")
                        st.cache_data.clear()
                        st.rerun()
                
                if submit_delete:
                    if api_request("DELETE", f"/appointments/{appt_id}"):
                        st.success("Cita eliminada.")
                        st.cache_data.clear()
                        st.rerun()