import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# --- 1. Protección de la Página ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Registros de Vacunación", page_icon="📋", layout="wide")
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
        if response.status_code != 404: 
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

# --- 4. Carga de Datos ---
pets_list = get_data("/pets/")
vaccines_list = get_data("/vaccines/")
vets_list = get_data("/veterinarians/")
records_list = get_data("/vaccination-records/")

pet_options = {f"{p['pet_id']} - {p['name']}": p['pet_id'] for p in pets_list} if pets_list else {}
vaccine_options = {f"{v['vaccine_id']} - {v['name']}": v['vaccine_id'] for v in vaccines_list} if vaccines_list else {}
vet_options = {f"{v['veterinarian_id']} - {v['first_name']} {v['last_name']}": v['veterinarian_id'] for v in vets_list} if vets_list else {}

# --- 5. Interfaz Principal ---
st.title("📋 Control de Vacunación")

tab_history, tab_register, tab_manage = st.tabs(["📖 Historial General", "💉 Registrar Aplicación", "✏️ Corregir / Eliminar"])

# --- TAB 1: HISTORIAL ---
with tab_history:
    st.subheader("Bitácora de Aplicaciones")
    if records_list:
        search_pet = st.text_input("🔍 Filtrar por nombre de mascota:", placeholder="Ej. Fido")
        data_processed = []
        for r in records_list:
            p_name = r['pet']['name'] if r.get('pet') else "Mascota Eliminada"
            v_name = r['vaccine']['name'] if r.get('vaccine') else "Vacuna Eliminada"
            doc_name = f"Dr. {r['veterinarian']['last_name']}" if r.get('veterinarian') else "N/A"
            
            if search_pet and search_pet.lower() not in p_name.lower():
                continue

            data_processed.append({
                "ID": r['vaccination_id'],
                "Fecha": r['vaccination_date'],
                "Mascota": p_name,
                "Vacuna": v_name,
                "Dosis": r.get('batch_number', 'N/A'),
                "Próxima": r.get('next_dose_date', '-'),
                "Veterinario": doc_name
            })
            
        if data_processed:
            st.dataframe(pd.DataFrame(data_processed).set_index("ID"), use_container_width=True)
        else:
            st.info("No se encontraron registros con ese filtro.")
    else:
        st.info("No hay registros de vacunación en el sistema.")

# --- TAB 2: REGISTRAR (CON VALIDACIÓN DE LOTE) ---
with tab_register:
    st.subheader("Nueva Aplicación de Vacuna")
    
    with st.form("new_record_form"):
        c1, c2 = st.columns(2)
        with c1:
            sel_pet = st.selectbox("Mascota*", options=list(pet_options.keys()))
            sel_vac = st.selectbox("Vacuna Aplicada*", options=list(vaccine_options.keys()))
            sel_vet = st.selectbox("Veterinario Responsable*", options=list(vet_options.keys()))
        
        with c2:
            in_date = st.date_input("Fecha de Aplicación*", value=date.today())
            in_next = st.date_input("Fecha Próximo Refuerzo", value=None)
            # --- CAMBIO: Marcamos visualmente que es obligatorio ---
            in_batch = st.text_input("Lote / Serie*") 

        submitted = st.form_submit_button("Guardar Registro")
        
        if submitted:
            # --- CAMBIO: Añadimos 'or not in_batch' a la validación ---
            if not sel_pet or not sel_vac or not sel_vet or not in_batch:
                st.error("Todos los campos marcados con * son obligatorios. Debes ingresar el número de Lote.")
            else:
                payload = {
                    "pet_id": pet_options[sel_pet],
                    "vaccine_id": vaccine_options[sel_vac],
                    "veterinarian_id": vet_options[sel_vet],
                    "vaccination_date": in_date.isoformat(),
                    "next_dose_date": in_next.isoformat() if in_next else None,
                    "batch_number": in_batch
                }
                
                if api_request("POST", "/vaccination-records/", data=payload):
                    st.success("✅ Vacunación registrada correctamente.")
                    st.cache_data.clear()
                    st.rerun()

# --- TAB 3: GESTIONAR ---
with tab_manage:
    st.subheader("Modificar Registro Existente")
    if records_list:
        rec_options = {}
        for r in records_list:
            p_name = r['pet']['name'] if r.get('pet') else "?"
            v_name = r['vaccine']['name'] if r.get('vaccine') else "?"
            label = f"ID: {r['vaccination_id']} | {r['vaccination_date']} | {p_name} - {v_name}"
            rec_options[label] = r['vaccination_id']
            
        selected_rec_label = st.selectbox("Buscar registro a editar:", options=list(rec_options.keys()))
        
        if selected_rec_label:
            rec_id = rec_options[selected_rec_label]
            current_rec = next((r for r in records_list if r['vaccination_id'] == rec_id), None)
            
            if current_rec:
                with st.form("edit_rec_form"):
                    st.info(f"Editando Registro ID: {rec_id}")
                    c1, c2 = st.columns(2)
                    with c1:
                        try:
                            def_date = datetime.strptime(current_rec['vaccination_date'], '%Y-%m-%d').date()
                            def_next = datetime.strptime(current_rec['next_dose_date'], '%Y-%m-%d').date() if current_rec['next_dose_date'] else None
                        except:
                            def_date = date.today()
                            def_next = None

                        edit_date = st.date_input("Fecha Aplicación", value=def_date)
                        edit_next = st.date_input("Próximo Refuerzo", value=def_next)
                    
                    with c2:
                        edit_batch = st.text_input("Lote / Serie", value=current_rec.get('batch_number', ''))

                    col_save, col_del = st.columns([1, 1])
                    with col_save:
                        update_btn = st.form_submit_button("💾 Guardar Cambios")
                    with col_del:
                        delete_btn = st.form_submit_button("🗑️ Eliminar Registro", type="primary")
                    
                    if update_btn:
                        # Validación también al editar
                        if not edit_batch:
                            st.error("El número de lote no puede estar vacío.")
                        else:
                            payload = {
                                "pet_id": current_rec['pet_id'],
                                "vaccine_id": current_rec['vaccine_id'],
                                "veterinarian_id": current_rec['veterinarian_id'],
                                "vaccination_date": edit_date.isoformat(),
                                "next_dose_date": edit_next.isoformat() if edit_next else None,
                                "batch_number": edit_batch
                            }
                            if api_request("PUT", f"/vaccination-records/{rec_id}", data=payload):
                                st.success("Registro actualizado.")
                                st.cache_data.clear()
                                st.rerun()
                            
                    if delete_btn:
                        if api_request("DELETE", f"/vaccination-records/{rec_id}"):
                            st.success("Registro eliminado.")
                            st.cache_data.clear()
                            st.rerun()
    else:
        st.info("No hay registros para modificar.")

# Botón flotante
st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")