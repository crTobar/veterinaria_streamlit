from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import auth, models, schemas, crud, database

# Esta es la URL donde el cliente (Streamlit/Postman) irá para obtener el token
# Le dice a FastAPI: "El endpoint de login está en '/login'"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_veterinarian(
    db: Session = Depends(database.get_db), 
    token: str = Depends(oauth2_scheme)
) -> models.Veterinarian:
    """
    Dependencia de FastAPI para obtener el usuario (Veterinario) actual a partir de un token JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Decodificar el token
    email = auth.decode_access_token(token)
    if email is None:
        raise credentials_exception
    
    # 2. Validar el schema (aunque ya lo hicimos, es buena práctica)
    token_data = schemas.TokenData(email=email)
    
    # 3. Obtener el usuario (Veterinario) de la base de datos
    user = crud.get_veterinarian_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
        
    return user

def get_current_active_veterinarian(
    current_user: models.Veterinarian = Depends(get_current_veterinarian)
) -> models.Veterinarian:
    """
    Dependencia que verifica si el usuario obtenido del token está activo.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user