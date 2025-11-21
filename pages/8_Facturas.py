import streamlit as st
import pandas as pd
import requests
import uuid
from datetime import datetime, date

# --- 1. Protección de la Página ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, inicia sesión para acceder.")
    st.stop()

# --- 2. Configuración ---
st.set_page_config(page_title="Gestión Financiera", page_icon="💰", layout="wide")
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
invoices_list = get_data("/invoices/")
appts_list = get_data("/appointments/") 

# --- 5. Interfaz Principal ---
st.title("💰 Gestión Financiera y Facturación")

# --- Métricas Clave ---
if invoices_list:
    df_inv = pd.DataFrame(invoices_list)
    df_inv['total_amount'] = pd.to_numeric(df_inv['total_amount'])
    
    total_facturado = df_inv['total_amount'].sum()
    total_pendiente = df_inv[df_inv['payment_status'].isin(['pending', 'overdue'])]['total_amount'].sum()
    total_pagado = df_inv[df_inv['payment_status'] == 'paid']['total_amount'].sum()
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Facturado", f"${total_facturado:,.2f}")
    kpi2.metric("Ingresos Reales", f"${total_pagado:,.2f}", delta="Efectivo")
    kpi3.metric("Pendiente de Cobro", f"${total_pendiente:,.2f}", delta="-Deuda", delta_color="inverse")
    
    st.divider()

# --- PESTAÑAS ---
tab_status, tab_create, tab_manage = st.tabs(["📊 Estado de Cuenta", "➕ Emitir Factura", "✏️ Administrar"])

# --- TAB 1: ESTADO DE CUENTA ---
with tab_status:
    st.subheader("Listado de Facturas")
    
    if invoices_list:
        c1, c2 = st.columns([3, 1])
        with c1:
            search_inv = st.text_input("🔍 Buscar por Número de Factura:", placeholder="INV-...")
        with c2:
            filter_status = st.selectbox("Estado de Pago", ["Todos", "pending", "paid", "overdue", "partial"])
        
        data_display = []
        for inv in invoices_list:
            if search_inv and search_inv.lower() not in inv['invoice_number'].lower():
                continue
            if filter_status != "Todos" and inv['payment_status'] != filter_status:
                continue
            
            appt_info = f"Cita #{inv['appointment_id']}" if inv.get('appointment_id') else "Servicio General"
            
            data_display.append({
                "ID": inv['invoice_id'],
                "Número": inv['invoice_number'],
                "Fecha": inv['issue_date'],
                "Concepto": appt_info,
                "Total": inv['total_amount'],
                "Estado": inv['payment_status'],
                "Fecha Pago": inv.get('payment_date') or "-"
            })
        
        df_display = pd.DataFrame(data_display)
        
        if not df_display.empty:
            st.dataframe(
                df_display.set_index("ID"),
                column_config={
                    "Total": st.column_config.NumberColumn("Monto Total", format="$%.2f"),
                },
                width='stretch'
            )
            
            st.markdown("#### 💳 Registrar Cobro")
            pending_invs = [i for i in data_display if i['Estado'] in ['pending', 'overdue', 'partial']]
            
            if pending_invs:
                c_pay1, c_pay2 = st.columns([3, 1])
                with c_pay1:
                    inv_to_pay_id = st.selectbox(
                        "Selecciona una factura pendiente:",
                        options=[p['ID'] for p in pending_invs],
                        format_func=lambda x: f"Factura #{next(p['Número'] for p in pending_invs if p['ID']==x)} - ${next(p['Total'] for p in pending_invs if p['ID']==x)}"
                    )
                with c_pay2:
                    st.write("") 
                    if st.button("✅ Registrar Pago Completo", type="primary", use_container_width=True):
                        with st.spinner("Procesando pago..."):
                            if api_request("POST", f"/invoices/{inv_to_pay_id}/pay"):
                                st.success("¡Pago registrado!")
                                st.cache_data.clear()
                                st.rerun()
            else:
                st.success("¡No hay facturas pendientes!")
        else:
            st.info("No se encontraron facturas.")
    else:
        st.info("No hay facturas en el sistema.")

# --- TAB 2: EMITIR FACTURA (REACTIVA / SIN FORM) ---
with tab_create:
    st.subheader("Emitir Nueva Factura")
    
    # --- NOTA: Quitamos 'with st.form' para que los cálculos sean inmediatos ---
    
    # Generar ID automático: INV-AAAAMMDD-XXXX
    # Usamos session_state para que el ID no cambie cada vez que escribes una letra
    if 'new_invoice_uuid' not in st.session_state:
        st.session_state['new_invoice_uuid'] = uuid.uuid4().hex[:4].upper()
        
    auto_inv_num = f"INV-{datetime.now().strftime('%Y%m%d')}-{st.session_state['new_invoice_uuid']}"
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.text_input("Número de Factura (Automático)", value=auto_inv_num, disabled=True)
        new_issue_date = st.date_input("Fecha de Emisión*", value=date.today())
        
        appt_opts = {f"Cita #{a['appointment_id']} ({a['appointment_date'][:10]})": a['appointment_id'] for a in appts_list}
        sel_appt_key = st.selectbox("Vincular a Cita (Opcional)", [None] + list(appt_opts.keys()))
        sel_appt_id = appt_opts[sel_appt_key] if sel_appt_key else None

    with c2:
        # Inputs numéricos fuera del formulario se actualizan al presionar Enter o salir del campo
        new_subtotal = st.number_input("Subtotal ($)*", min_value=0.0, step=10.0, value=0.0)
        new_tax_rate = st.number_input("Impuesto (%)", value=13.0, step=1.0)
        
        # --- CÁLCULO EN TIEMPO REAL ---
        calc_tax = new_subtotal * (new_tax_rate / 100)
        calc_total = new_subtotal + calc_tax
        
        st.markdown("---")
        col_tax, col_tot = st.columns(2)
        col_tax.metric("Impuesto", f"${calc_tax:,.2f}")
        col_tot.metric("Total a Pagar", f"${calc_total:,.2f}")
        st.markdown("---")

    new_status = st.selectbox("Estado Inicial", ["pending", "paid", "partial"])

    # Botón normal (no form_submit_button)
    if st.button("Emitir Factura", type="primary"):
        if new_subtotal <= 0:
            st.error("El subtotal debe ser mayor a 0.")
        else:
            payload = {
                "appointment_id": sel_appt_id,
                "invoice_number": auto_inv_num,
                "issue_date": new_issue_date.isoformat(),
                "subtotal": new_subtotal,
                "tax_amount": calc_tax,
                "total_amount": calc_total,
                "payment_status": new_status,
                "payment_date": datetime.now().isoformat() if new_status == 'paid' else None
            }
            
            if api_request("POST", "/invoices/", data=payload):
                st.success(f"Factura {auto_inv_num} emitida correctamente.")
                # Limpiar el ID generado para la próxima factura
                del st.session_state['new_invoice_uuid']
                st.cache_data.clear()
                st.rerun()

# --- TAB 3: ADMINISTRAR ---
with tab_manage:
    st.subheader("Corrección o Anulación")
    
    if invoices_list:
        inv_options = {f"{i['invoice_id']} - {i['invoice_number']} (${i['total_amount']})": i['invoice_id'] for i in invoices_list}
        sel_edit_key = st.selectbox("Buscar Factura:", options=list(inv_options.keys()))
        
        if sel_edit_key:
            inv_id = inv_options[sel_edit_key]
            curr_inv = next((i for i in invoices_list if i['invoice_id'] == inv_id), None)
            
            if curr_inv:
                st.info(f"Gestionando Factura: {curr_inv['invoice_number']}")
                
                with st.form("edit_invoice_form"):
                    edit_status = st.selectbox("Estado de Pago", ["pending", "paid", "overdue", "partial"], 
                                             index=["pending", "paid", "overdue", "partial"].index(curr_inv['payment_status']))
                    
                    st.caption("Para modificar montos, anula y re-emite.")
                    
                    c_upd, c_del = st.columns([1, 1])
                    with c_upd:
                        btn_update = st.form_submit_button("Actualizar Estado")
                    with c_del:
                        btn_delete = st.form_submit_button("🗑️ Anular (Eliminar)", type="primary")
                    
                    if btn_update:
                        payload = {"payment_status": edit_status}
                        if api_request("PUT", f"/invoices/{inv_id}", data=payload):
                            st.success("Estado actualizado.")
                            st.cache_data.clear()
                            st.rerun()
                    
                    if btn_delete:
                        if api_request("DELETE", f"/invoices/{inv_id}"):
                            st.success("Factura anulada.")
                            st.cache_data.clear()
                            st.rerun()

st.markdown("---")
if st.button("⬅️ Volver al Menú Principal"):
    st.switch_page("pages/1_Menu_Principal.py")