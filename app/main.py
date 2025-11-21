from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from decimal import Decimal
# ---  IMPORTS PARA RATE LIMITING ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

# Importaciones locales
from . import crud, models, schemas, auth, security
from .database import engine, get_db
# --- CONFIGURACIÓN DE RATE LIMITER ---
# Inicializa el limiter y le dice que use Redis en localhost
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")

app = FastAPI(title="API Clínica Veterinaria")

# --- MANEJADOR DE ERRORES Y ESTADO DEL LIMITER ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Alias de Dependencia ---
DbDep = Depends(get_db)

# --- NUEVO: Alias para la dependencia de usuario activo ---
# Este es el "guardia de seguridad" que pondremos en cada endpoint
ActiveUserDep = Depends(security.get_current_active_veterinarian)

# ==========================================
# === ENDPOINTS DE AUTENTICACIÓN (M6) ===
# ==========================================

@app.post("/login", response_model=schemas.Token, tags=["Authentication"])
@limiter.limit("5/minute")
async def login_for_access_token(
    request: Request,
    db: Session = DbDep,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Inicia sesión de un veterinario (email como username) y devuelve un token JWT.
    """
    # 1. Busca al veterinario por su email (que viene en 'form_data.username')
    user = crud.get_veterinarian_by_email(db, email=form_data.username)
    
    # 2. Verifica que el usuario exista y la contraseña sea correcta
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Crea el token JWT
    access_token = auth.create_access_token(
        data={"sub": user.email} # 'sub' (subject) es el email
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/sign-up", response_model=schemas.Veterinarian, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
@limiter.limit("10/hour")
def sign_up_veterinarian(request: Request, vet: schemas.VeterinarianCreate, db: Session = DbDep):
    """
    Crea un nuevo usuario Veterinario (Sign-up).
    Usa el 'create_veterinarian' del CRUD que ya modificamos.
    """
    if crud.get_veterinarian_by_email(db, email=vet.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if crud.get_veterinarian_by_license(db, license_number=vet.license_number):
        raise HTTPException(status_code=400, detail="License number already registered")
    return crud.create_veterinarian(db=db, vet=vet)

@app.post("/recover-password", status_code=status.HTTP_200_OK, tags=["Authentication"])
@limiter.limit("3/hour")
def recover_password(request: Request, recovery_data: schemas.PasswordRecoveryRequest, db: Session = DbDep):
    """
    Recupera contraseña. (Simulación: Muestra la nueva contraseña en la consola de la API).
    """
    user = crud.get_veterinarian_by_email(db, email=recovery_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Generar una nueva contraseña aleatoria (simple)
    new_password = "new_password_123" # En un caso real, esto sería aleatorio
    user.hashed_password = auth.get_password_hash(new_password)
    db.add(user)
    db.commit()
    
    # --- MUESTRA LA CONTRASEÑA EN LA CONSOLA DEL SERVIDOR (Uvicorn) ---
    print(f"RECUPERACIÓN DE CONTRASEÑA para {user.email}: Nueva contraseña es -> {new_password}")
    # ------------------------------------------------------------------
    
    return {"message": "Se ha generado una nueva contraseña. Revise la consola del servidor."}

@app.get("/users/me", response_model=schemas.Veterinarian, tags=["Authentication"])
@limiter.limit("100/minute")
def read_users_me(request: Request, current_user: models.Veterinarian = ActiveUserDep):
    """
    Endpoint protegido que devuelve la información del usuario (vet) 
    que está actualmente logueado (basado en el token).
    """
    return current_user

# === Endpoints Veterinarians ===


@app.get("/veterinarians/", response_model=List[schemas.Veterinarian], tags=["Veterinarians"])
@limiter.limit("100/minute")
def read_veterinarians(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_veterinarians(db, skip=skip, limit=limit)

@app.get("/veterinarians/{vet_id}", response_model=schemas.Veterinarian, tags=["Veterinarians"])
@limiter.limit("100/minute")
def read_veterinarian(request: Request, vet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vet = crud.get_veterinarian(db, vet_id=vet_id)
    if db_vet is None:
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    return db_vet

@app.put("/veterinarians/{vet_id}", response_model=schemas.Veterinarian, tags=["Veterinarians"])
@limiter.limit("100/minute")
def update_veterinarian(request: Request, vet_id: int, vet: schemas.VeterinarianUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vet = crud.get_veterinarian(db, vet_id=vet_id)
    if db_vet is None:
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    if vet.email and vet.email != db_vet.email and crud.get_veterinarian_by_email(db, email=vet.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if vet.license_number and vet.license_number != db_vet.license_number and crud.get_veterinarian_by_license(db, license_number=vet.license_number):
        raise HTTPException(status_code=400, detail="License number already registered")
    return crud.update_veterinarian(db=db, db_vet=db_vet, vet_update=vet)

@app.delete("/veterinarians/{vet_id}", response_model=schemas.Veterinarian, tags=["Veterinarians"])
@limiter.limit("100/minute")
def delete_veterinarian(request: Request, vet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vet = crud.get_veterinarian(db, vet_id=vet_id)
    if db_vet is None:
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    deleted_vet = crud.delete_veterinarian(db=db, db_vet=db_vet)
    if deleted_vet is None:
        raise HTTPException(status_code=400, detail="Cannot delete veterinarian with active appointments")
    return deleted_vet

@app.get("/veterinarians/{vet_id}/appointments", response_model=List[schemas.Appointment], tags=["Veterinarians"])
@limiter.limit("100/minute")
def read_vet_appointments(request: Request, vet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_veterinarian(db, vet_id=vet_id):
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    return crud.get_appointments_by_veterinarian(db=db, vet_id=vet_id)

@app.get("/veterinarians/{vet_id}/schedule", response_model=List[schemas.Appointment], tags=["Veterinarians"])
@limiter.limit("100/minute")
def read_vet_schedule(request: Request, vet_id: int, date: date, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_veterinarian(db, vet_id=vet_id):
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    return crud.get_appointments_by_vet_and_date(db=db, vet_id=vet_id, date=date)

# === Endpoints Owners ===
@app.post("/owners/", response_model=schemas.Owner, status_code=status.HTTP_201_CREATED, tags=["Owners"])
@limiter.limit("100/minute")
def create_owner(request: Request, owner: schemas.OwnerCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if crud.get_owner_by_email(db, email=owner.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_owner(db=db, owner=owner)

@app.get("/owners/", response_model=List[schemas.Owner], tags=["Owners"])
@limiter.limit("100/minute")
def read_owners(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_owners(db, skip=skip, limit=limit)

@app.get("/owners/{owner_id}", response_model=schemas.Owner, tags=["Owners"])
@limiter.limit("100/minute")
def read_owner(request: Request, owner_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_owner = crud.get_owner(db, owner_id=owner_id)
    if db_owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    return db_owner

@app.put("/owners/{owner_id}", response_model=schemas.Owner, tags=["Owners"])
@limiter.limit("100/minute")
def update_owner(request: Request, owner_id: int, owner: schemas.OwnerUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_owner = crud.get_owner(db, owner_id=owner_id)
    if db_owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    if owner.email and owner.email != db_owner.email and crud.get_owner_by_email(db, email=owner.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.update_owner(db=db, db_owner=db_owner, owner_update=owner)

@app.delete("/owners/{owner_id}", response_model=schemas.Owner, tags=["Owners"])
@limiter.limit("100/minute")
def delete_owner(request: Request, owner_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_owner = crud.get_owner(db, owner_id=owner_id)
    if db_owner is None:
        raise HTTPException(status_code=404, detail="Owner not found")
    deleted_owner = crud.delete_owner(db=db, db_owner=db_owner)
    if deleted_owner is None:
        raise HTTPException(status_code=400, detail="Cannot delete owner with associated pets")
    return deleted_owner

@app.get("/owners/{owner_id}/pets", response_model=List[schemas.Pet], tags=["Owners"])
@limiter.limit("100/minute")
def read_owner_pets(request: Request, owner_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_owner(db, owner_id=owner_id):
        raise HTTPException(status_code=404, detail="Owner not found")
    return crud.get_pets_by_owner(db=db, owner_id=owner_id)

@app.get("/owners/{owner_id}/appointments", response_model=List[schemas.Appointment], tags=["Owners"])
@limiter.limit("100/minute")
def read_owner_appointments(request: Request, owner_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_owner(db, owner_id=owner_id):
        raise HTTPException(status_code=404, detail="Owner not found")
    return crud.get_appointments_by_owner(db=db, owner_id=owner_id)

# === Endpoints Pets ===
@app.post("/pets/", response_model=schemas.Pet, status_code=status.HTTP_201_CREATED, tags=["Pets"])
@limiter.limit("100/minute")
def create_pet(request: Request, pet: schemas.PetCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_owner(db, owner_id=pet.owner_id):
        raise HTTPException(status_code=400, detail=f"Owner with id {pet.owner_id} not found")
    created_pet = crud.create_pet(db=db, pet=pet)
    return crud.get_pet(db, created_pet.pet_id)

@app.get("/pets/", response_model=List[schemas.Pet], tags=["Pets"])
@limiter.limit("100/minute")
def read_pets(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_pets(db, skip=skip, limit=limit)

@app.get("/pets/{pet_id}", response_model=schemas.Pet, tags=["Pets"])
@limiter.limit("100/minute")
def read_pet(request: Request, pet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_pet = crud.get_pet(db, pet_id=pet_id)
    if db_pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return db_pet

@app.put("/pets/{pet_id}", response_model=schemas.Pet, tags=["Pets"])
@limiter.limit("100/minute")
def update_pet(request: Request, pet_id: int, pet: schemas.PetUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_pet = crud.get_pet(db, pet_id=pet_id)
    if db_pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    if pet.owner_id and pet.owner_id != db_pet.owner_id and not crud.get_owner(db, owner_id=pet.owner_id):
        raise HTTPException(status_code=400, detail=f"Owner with id {pet.owner_id} not found")
    updated_pet = crud.update_pet(db=db, db_pet=db_pet, pet_update=pet)
    return crud.get_pet(db, updated_pet.pet_id)

@app.delete("/pets/{pet_id}", response_model=schemas.Pet, tags=["Pets"])
@limiter.limit("100/minute")
def delete_pet(request: Request, pet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_pet = crud.get_pet(db, pet_id=pet_id)
    if db_pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    deleted_pet = crud.delete_pet(db=db, db_pet=db_pet)
    if deleted_pet is None:
        raise HTTPException(status_code=400, detail="Cannot delete pet with active appointments")
    return deleted_pet

# --- Endpoints Relacionales de Pets (M1, M2) ---
@app.get("/pets/{pet_id}/medical-history", response_model=List[schemas.MedicalRecord], tags=["Pets", "Medical Records"])
@limiter.limit("100/minute")
def read_pet_medical_history(request: Request, pet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_pet(db, pet_id=pet_id):
        raise HTTPException(status_code=404, detail="Pet not found")
    return crud.get_medical_records_by_pet(db=db, pet_id=pet_id)

@app.get("/pets/{pet_id}/vaccinations", response_model=List[schemas.VaccinationRecord], tags=["Pets", "Vaccination Records"])
@limiter.limit("100/minute")
def read_pet_vaccinations(request: Request, pet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_pet(db, pet_id=pet_id):
        raise HTTPException(status_code=404, detail="Pet not found")
    return crud.get_vaccinations_by_pet(db=db, pet_id=pet_id)

@app.get("/pets/{pet_id}/vaccination-schedule", response_model=List[schemas.VaccinationRecord], tags=["Pets", "Vaccination Records"])
@limiter.limit("100/minute")
def read_pet_vaccination_schedule(request: Request, pet_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_pet(db, pet_id=pet_id):
        raise HTTPException(status_code=404, detail="Pet not found")
    return crud.get_vaccination_schedule_by_pet(db=db, pet_id=pet_id)


# === Endpoints Appointments ===
@app.post("/appointments/", response_model=schemas.Appointment, status_code=status.HTTP_201_CREATED, tags=["Appointments"])
@limiter.limit("100/minute")
def create_appointment(request: Request, appt: schemas.AppointmentCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    
    # --- CORRECCIÓN PARA EMERGENCIAS ---
    # Solo verificamos la mascota si pet_id NO es None
    if appt.pet_id is not None:
        if not crud.get_pet(db, pet_id=appt.pet_id):
             raise HTTPException(status_code=404, detail=f"Pet with id {appt.pet_id} not found")
    # -----------------------------------

    if not crud.get_veterinarian(db, vet_id=appt.veterinarian_id):
        raise HTTPException(status_code=404, detail=f"Veterinarian with id {appt.veterinarian_id} not found")
    
    # Intenta crear la cita
    created_appt = crud.create_appointment(db=db, appt=appt)
    
    if created_appt is None:
        # Si crud.create_appointment devuelve None, algo falló internamente
        raise HTTPException(status_code=400, detail="Could not create appointment")
    
    return crud.get_appointment(db, created_appt.appointment_id)

@app.get("/appointments/", response_model=List[schemas.Appointment], tags=["Appointments"])
@limiter.limit("100/minute")
def read_appointments(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_appointments(db, skip=skip, limit=limit)

@app.get("/appointments/today", response_model=List[schemas.Appointment], tags=["Appointments"])
@limiter.limit("100/minute")
def read_appointments_today(request: Request, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_appointments_by_status_or_date(db=db, date=date.today())

@app.get("/appointments/pending", response_model=List[schemas.Appointment], tags=["Appointments"])
@limiter.limit("100/minute")
def read_pending_appointments(request: Request, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_appointments_by_status_or_date(db=db, status='scheduled')

@app.get("/appointments/{appt_id}", response_model=schemas.Appointment, tags=["Appointments"])
@limiter.limit("100/minute")
def read_appointment(request: Request, appt_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appt = crud.get_appointment(db, appt_id=appt_id)
    if db_appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return db_appt

@app.put("/appointments/{appt_id}", response_model=schemas.Appointment, tags=["Appointments"])
@limiter.limit("100/minute")
def update_appointment(request: Request, appt_id: int, appt: schemas.AppointmentUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appt = crud.get_appointment(db, appt_id=appt_id)
    if db_appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.pet_id and appt.pet_id != db_appt.pet_id and not crud.get_pet(db, pet_id=appt.pet_id):
        raise HTTPException(status_code=400, detail=f"Pet with id {appt.pet_id} not found")
    if appt.veterinarian_id and appt.veterinarian_id != db_appt.veterinarian_id and not crud.get_veterinarian(db, vet_id=appt.veterinarian_id):
        raise HTTPException(status_code=400, detail=f"Veterinarian with id {appt.veterinarian_id} not found")
    
    updated_appt = crud.update_appointment(db=db, db_appt=db_appt, appt_update=appt)
    return crud.get_appointment(db, updated_appt.appointment_id) # Recargar

@app.put("/appointments/{appt_id}/complete", response_model=schemas.Appointment, tags=["Appointments"])
@limiter.limit("100/minute")
def complete_appointment(request: Request, appt_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appt = crud.get_appointment(db, appt_id=appt_id)
    if db_appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    update_data = schemas.AppointmentUpdate(status=schemas.AppointmentStatusEnum.completed)
    return crud.update_appointment(db=db, db_appt=db_appt, appt_update=update_data)

@app.put("/appointments/{appt_id}/cancel", response_model=schemas.Appointment, tags=["Appointments"])
@limiter.limit("100/minute")
def cancel_appointment(request: Request, appt_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appt = crud.get_appointment(db, appt_id=appt_id)
    if db_appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Lógica de negocio: revertir métricas si se cancela
    # (Asumiendo que delete_appointment hace lo mismo)
    deleted_appt = crud.delete_appointment(db=db, db_appt=db_appt)
    # Marcarla como cancelada en lugar de borrarla (mejor)
    # update_data = schemas.AppointmentUpdate(status=schemas.AppointmentStatusEnum.cancelled)
    # return crud.update_appointment(db=db, db_appt=db_appt, appt_update=update_data)
    
    # Para este ejercicio, seguir el delete_appointment que revierte métricas
    return deleted_appt 

@app.delete("/appointments/{appt_id}", response_model=schemas.Appointment, tags=["Appointments"])
@limiter.limit("100/minute")
def delete_appointment(request: Request, appt_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appt = crud.get_appointment(db, appt_id=appt_id)
    if db_appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return crud.delete_appointment(db=db, db_appt=db_appt)


# === Endpoints Medical Records (M1) ===
@app.post("/medical-records/", response_model=schemas.MedicalRecord, status_code=status.HTTP_201_CREATED, tags=["Medical Records"])
@limiter.limit("100/minute")
def create_medical_record(request: Request, record: schemas.MedicalRecordCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_appointment = crud.get_appointment(db, appt_id=record.appointment_id)
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if db_appointment.status != 'completed':
        raise HTTPException(status_code=400, detail="Cannot create medical record for an appointment that is not completed")
    if crud.get_medical_record_by_appointment(db, appointment_id=record.appointment_id):
        raise HTTPException(status_code=400, detail="A medical record already exists for this appointment")
    return crud.create_medical_record(db=db, record=record)

@app.get("/medical-records/", response_model=List[schemas.MedicalRecord], tags=["Medical Records"])
@limiter.limit("100/minute")
def read_medical_records(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return db.query(models.MedicalRecord).offset(skip).limit(limit).all()

@app.get("/medical-records/{record_id}", response_model=schemas.MedicalRecord, tags=["Medical Records"])
@limiter.limit("100/minute")
def read_medical_record(request: Request, record_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_record = crud.get_medical_record(db, record_id=record_id)
    if db_record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    return db_record

@app.put("/medical-records/{record_id}", response_model=schemas.MedicalRecord, tags=["Medical Records"])
@limiter.limit("100/minute")
def update_medical_record(request: Request, record_id: int, record: schemas.MedicalRecordUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_record = crud.get_medical_record(db, record_id=record_id)
    if db_record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    return crud.update_medical_record(db=db, db_record=db_record, record_update=record)


# === Endpoints Vaccines (M2) ===
@app.post("/vaccines/", response_model=schemas.Vaccine, status_code=status.HTTP_201_CREATED, tags=["Vaccines"])
@limiter.limit("100/minute")
def create_vaccine(request: Request, vaccine: schemas.VaccineCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vaccine = crud.get_vaccine_by_name(db, name=vaccine.name)
    if db_vaccine:
        raise HTTPException(status_code=400, detail="Vaccine name already registered")
    return crud.create_vaccine(db=db, vaccine=vaccine)

@app.get("/vaccines/", response_model=List[schemas.Vaccine], tags=["Vaccines"])
@limiter.limit("100/minute")
def read_vaccines(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_vaccines(db, skip=skip, limit=limit)

@app.put("/vaccines/{vaccine_id}", response_model=schemas.Vaccine, tags=["Vaccines"])
@limiter.limit("100/minute")
def update_vaccine(request: Request, vaccine_id: int, vaccine: schemas.VaccineCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vaccine = crud.get_vaccine(db, vaccine_id=vaccine_id)
    if db_vaccine is None:
        raise HTTPException(status_code=404, detail="Vaccine not found")
    
    # Usamos update_db_item que ya tienes en crud.py, aunque no haya un update_vaccine específico
    # Podemos hacerlo manual o crear la función en crud. 
    # Opción rápida (usando lógica existente):
    update_data = vaccine.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vaccine, key, value)
    db.commit()
    db.refresh(db_vaccine)
    return db_vaccine

@app.delete("/vaccines/{vaccine_id}", response_model=schemas.Vaccine, tags=["Vaccines"])
@limiter.limit("100/minute")
def delete_vaccine(request: Request, vaccine_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_vaccine = crud.get_vaccine(db, vaccine_id=vaccine_id)
    if db_vaccine is None:
        raise HTTPException(status_code=404, detail="Vaccine not found")
    
    # Verificar si se usa en registros (opcional pero recomendado)
    if db_vaccine.vaccination_records:
         raise HTTPException(status_code=400, detail="Cannot delete vaccine used in vaccination records")

    db.delete(db_vaccine)
    db.commit()
    return db_vaccine


# === Endpoints Vaccination Records (M2) ===
@app.post("/vaccination-records/", response_model=schemas.VaccinationRecord, status_code=status.HTTP_201_CREATED, tags=["Vaccination Records"])
@limiter.limit("100/minute")
def create_vaccination_record(request: Request, record: schemas.VaccinationRecordCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    if not crud.get_pet(db, pet_id=record.pet_id):
        raise HTTPException(status_code=404, detail="Pet not found")
    if not crud.get_vaccine(db, vaccine_id=record.vaccine_id):
        raise HTTPException(status_code=404, detail="Vaccine not found")
    if not crud.get_veterinarian(db, vet_id=record.veterinarian_id):
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    
    created_record = crud.create_vaccination_record(db=db, record=record)
    return crud.get_vaccination_record(db, record_id=created_record.vaccination_id)

@app.get("/vaccination-records/", response_model=List[schemas.VaccinationRecord], tags=["Vaccination Records"])
@limiter.limit("100/minute")
def read_vaccination_records(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_vaccination_records(db, skip=skip, limit=limit)

@app.put("/vaccination-records/{record_id}", response_model=schemas.VaccinationRecord, tags=["Vaccination Records"])
@limiter.limit("100/minute")
def update_vaccination_record(request: Request, record_id: int, record: schemas.VaccinationRecordCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_record = crud.get_vaccination_record(db, record_id=record_id)
    if db_record is None:
        raise HTTPException(status_code=404, detail="Vaccination record not found")
    return crud.update_vaccination_record(db=db, db_record=db_record, record_update=record)

@app.delete("/vaccination-records/{record_id}", response_model=schemas.VaccinationRecord, tags=["Vaccination Records"])
@limiter.limit("100/minute")
def delete_vaccination_record(request: Request, record_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_record = crud.get_vaccination_record(db, record_id=record_id)
    if db_record is None:
        raise HTTPException(status_code=404, detail="Vaccination record not found")
    return crud.delete_vaccination_record(db=db, db_record=db_record)


# === Endpoints Invoices (M4) ===
@app.get("/invoices/", response_model=List[schemas.Invoice], tags=["Invoices"])
@limiter.limit("100/minute")
def read_invoices(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_invoices(db, skip=skip, limit=limit)

@app.get("/invoices/pending", response_model=List[schemas.Invoice], tags=["Invoices"])
@limiter.limit("100/minute")
def read_pending_invoices(request: Request, skip: int = 0, limit: int = 100, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    return crud.get_pending_invoices(db, skip=skip, limit=limit)

@app.get("/invoices/{invoice_id}", response_model=schemas.Invoice, tags=["Invoices"])
@limiter.limit("100/minute")
def read_invoice(request: Request, invoice_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_invoice = crud.get_invoice(db, invoice_id=invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return db_invoice

@app.post("/invoices/{invoice_id}/pay", response_model=schemas.Invoice, tags=["Invoices"])
@limiter.limit("100/minute")
def pay_invoice(request: Request, invoice_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_invoice = crud.get_invoice(db, invoice_id=invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if db_invoice.payment_status == 'paid':
        raise HTTPException(status_code=400, detail="Invoice is already paid")
    return crud.mark_invoice_as_paid(db=db, db_invoice=db_invoice)


@app.post("/invoices/", response_model=schemas.Invoice, status_code=status.HTTP_201_CREATED, tags=["Invoices"])
@limiter.limit("100/minute")
def create_invoice(request: Request, invoice: schemas.InvoiceCreate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    # Validaciones opcionales (ej. verificar si la cita existe)
    if invoice.appointment_id and not crud.get_appointment(db, appt_id=invoice.appointment_id):
         raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Verificar duplicados de número de factura
    # (Necesitarías una función get_invoice_by_number en crud, o confiar en el error de BD)
    
    return crud.create_invoice(db=db, invoice=invoice)

@app.put("/invoices/{invoice_id}", response_model=schemas.Invoice, tags=["Invoices"])
@limiter.limit("100/minute")
def update_invoice(request: Request, invoice_id: int, invoice: schemas.InvoiceUpdate, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_invoice = crud.get_invoice(db, invoice_id=invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Usamos la función genérica de update
    update_data = invoice.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@app.delete("/invoices/{invoice_id}", response_model=schemas.Invoice, tags=["Invoices"])
@limiter.limit("100/minute")
def delete_invoice(request: Request, invoice_id: int, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    db_invoice = crud.get_invoice(db, invoice_id=invoice_id)
    if db_invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db.delete(db_invoice)
    db.commit()
    return db_invoice


# === Endpoints Reports (M5) ===
@app.get("/reports/revenue", response_model=schemas.RevenueReport, tags=["Reports"])
@limiter.limit("100/minute")
def report_revenue(request: Request, start_date: date, end_date: date, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    total = crud.get_revenue_report(db, start_date=start_date, end_date=end_date)
    return schemas.RevenueReport(start_date=start_date, end_date=end_date, total_revenue=total)

@app.get("/reports/popular-veterinarians", response_model=List[schemas.Veterinarian], tags=["Reports"])
@limiter.limit("100/minute")
def report_popular_veterinarians(request: Request, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    # Simplemente devuelve los Vets ordenados por 'total_appointments'
    return crud.get_popular_veterinarians(db)

@app.get("/reports/vaccination-alerts", response_model=List[schemas.VaccinationRecord], tags=["Reports"])
@limiter.limit("100/minute")
def report_vaccination_alerts(request: Request, db: Session = DbDep, current_user: models.Veterinarian = ActiveUserDep):
    # Por defecto, busca vacunas para los próximos 30 días
    return crud.get_vaccination_alerts(db)