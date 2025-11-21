import streamlit as st
import requests
import time

# --- Configuración de la Página (Importante: layout="centered") ---
st.set_page_config(
    page_title="Bigotes y Colas - Login",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# URL base de tu API
API_URL = "http://127.0.0.1:8000"

# --- Inicialización de Sesión ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['auth_token'] = None

# --- Función de Login (Lógica) ---
def login_user(email, password):
    try:
        login_data = {'username': email, 'password': password}
        response = requests.post(f"{API_URL}/login", data=login_data)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception:
        return None

# --- VISTA: PÁGINA DE LOGIN  ---
def show_login_page():
    # 1. Inyectar CSS para el estilo visual
    st.markdown("""
        <style>
            /* Centrar y limitar el ancho del contenedor principal */
            .block-container {
                padding-top: 3rem;
                padding-bottom: 0rem;
                max-width: 400px;
            }
            
            /* Estilo del Título (Logo) */
            .login-title {
                font-family: 'Segoe UI', sans-serif;
                text-align: center;
                font-size: 2.5rem;
                font-weight: 600;
                margin-bottom: 30px;
            }
            
            /* Estilo de los Inputs */
            .stTextInput input {
                border-radius: 4px;
                border: 1px solid #363636;
                background-color: #121212;
                color: white;
            }
            
            /* --- ESTILOS DEL BOTÓN (AQUÍ ESTÁ EL CAMBIO) --- */
            
            /* 1. Estado Normal (Azul Instagram Original) */
            /* Si quieres que sea morado desde el inicio, cambia este color también */
            .stButton button {
                width: 100%;
                background-color: #0095f6; 
                color: white;
                font-weight: 600;
                border-radius: 8px;
                border: none;
                padding: 0.5rem 1rem;
                transition: background-color 0.3s ease; /* Transición suave */
            }
            
            /* 2. Al pasar el mouse (Hover) -> Morado Suave */
            .stButton button:hover {
                background-color: #9F7AEA !important; /* Morado suave */
                color: white !important;
                border: none;
            }

            /* 3. Al hacer clic (Active) -> Morado Oscuro */
            .stButton button:active {
                background-color: #553C9A !important; /* Morado oscuro */
                color: white !important;
                border: none;
            }

            /* Al tener el foco (tabulación) */
            .stButton button:focus {
                background-color: #9F7AEA !important;
                color: white !important;
                border: none;
                box-shadow: none;
            }
            
            /* Ocultar elementos extra de Streamlit */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    # ... (El resto de la función sigue igual: Logo, Formulario, etc.) ...

    # 2. El Logo / Título
    st.markdown("<div class='login-title'>Bigotes y Colas 🐾</div>", unsafe_allow_html=True)

    # 3. El Formulario
    with st.container(): # Contenedor simple
        with st.form("login_form", clear_on_submit=False):
            
            # Inputs sin etiquetas visibles (usando placeholder simulado con el label)
            email = st.text_input("Usuario o correo electrónico", placeholder="Teléfono, usuario o correo electrónico")
            password = st.text_input("Contraseña", type="password", placeholder="Contraseña")
            
            st.write("") # Pequeño espacio
            
            # Botón de acción
            submitted = st.form_submit_button("Iniciar sesión")
            
            if submitted:
                if not email or not password:
                    st.error("Por favor ingresa tus credenciales.")
                else:
                    with st.spinner(""): # Spinner discreto
                        token = login_user(email, password)
                        time.sleep(0.5) # Pequeña pausa estética
                        
                        if token:
                            st.session_state['logged_in'] = True
                            st.session_state['auth_token'] = token
                            st.rerun()
                        else:
                            st.error("La contraseña es incorrecta. Compruébala.")

    # 4. Links de "Olvidé contraseña" y "Registro"
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; font-size: 0.85rem;'><a href='#' style='color: #e0f1ff; text-decoration: none;'>¿Has olvidado la contraseña?</a></div>", unsafe_allow_html=True)
    
    st.markdown("---") # Línea divisoria
    
    col1, col2 = st.columns([1.5, 1]) # Centrar el texto de registro
    st.markdown(
        """
        <div style='text-align: center; font-size: 0.9rem; color: gray;'>
            ¿No tienes una cuenta? <a href='#' style='color: #0095f6; text-decoration: none; font-weight: 600;'>Regístrate</a>
        </div>
        """, 
        unsafe_allow_html=True
    )

# --- CONTROLADOR PRINCIPAL ---

if not st.session_state['logged_in']:
    show_login_page()
else:
    # Aquí iría tu función show_main_menu() o la redirección a pages/
    st.success("¡Bienvenido al sistema!")
    st.write("Redirigiendo al menú principal...")
    time.sleep(1)
    st.switch_page("pages/1_Menu_Principal.py") # Asegúrate de tener esta página creada