import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt

# --- Configuración de Seguridad ---

# 1. Algoritmo de Hashing de Contraseñas
# Usamos bcrypt, que es el estándar de la industria
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Configuración de Tokens JWT (JSON Web Token)
# Esta es tu "llave secreta". ¡DEBE ser secreta!
# En un proyecto real, la pones en un archivo .env, no aquí.
SECRET_KEY = "tu-llave-secreta-debe-ser-muy-larga-y-aleatoria" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 # El token durará 60 minutos

# --- Funciones de Utilidad ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara una contraseña en texto plano con un hash existente.
    Devuelve True si coinciden, False si no.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Genera un hash (encripta) una contraseña en texto plano.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un nuevo token JWT.
    'data' es el diccionario que queremos guardar dentro del token (ej. el email del veterinario).
    """
    to_encode = data.copy()
    
    # Establecer el tiempo de expiración
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    
    # Codificar el token con la llave secreta y el algoritmo
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    """
    Decodifica un token. Si es válido, devuelve el 'sub' (el email del usuario).
    Si es inválido o ha expirado, lanza una excepción.
    """
    try:
        # Intenta decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extrae el 'subject' (quién es el usuario)
        email: str = payload.get("sub")
        if email is None:
            return None # El token no tiene un 'sub'
            
        return email
    except JWTError:
        # El token es inválido (expirado, firma incorrecta, etc.)
        return None