from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract
from . import models, schemas
from datetime import date, datetime, timedelta
from decimal import Decimal

# --- Utils ---
def update_db_item(db_item, update_data):
    """Actualiza un item de la BD con datos de un schema Update."""
    update_data_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_data_dict.items():
        setattr(db_item, key, value)
    return db_item

# --- CRUD Veterinarians ---
def get_veterinarian(db: Session, vet_id: int):
    return db.query(models.Veterinarian).filter(models.Veterinarian.veterinarian_id == vet_id).first()

def get_veterinarian_by_email(db: Session, email: str):
    return db.query(models.Veterinarian).filter(models.Veterinarian.email == email).first()

def get_veterinarian_by_license(db: Session, license_number: str):
    return db.query(models.Veterinarian).filter(models.Veterinarian.license_number == license_number).first()

def get_veterinarians(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Veterinarian).offset(skip).limit(limit).all()

def create_veterinarian(db: Session, vet: schemas.VeterinarianCreate):
    db_vet = models.Veterinarian(**vet.model_dump())
    db.add(db_vet)
    db.commit()
    db.refresh(db_vet)
    return db_vet

def update_veterinarian(db: Session, db_vet: models.Veterinarian, vet_update: schemas.VeterinarianUpdate):
    db_vet = update_db_item(db_vet, vet_update)
    db.commit()
    db.refresh(db_vet)
    return db_vet

def delete_veterinarian(db: Session, db_vet: models.Veterinarian):
    # Lógica de borrado (ej. no borrar si tiene citas activas)
    active_appointments = db.query(models.Appointment).filter(
        models.Appointment.veterinarian_id == db_vet.veterinarian_id,
        models.Appointment.status == 'scheduled'
    ).count()
    if active_appointments > 0:
        return None # Indica fallo
        
    db.delete(db_vet)
    db.commit()
    return db_vet

def get_appointments_by_veterinarian(db: Session, vet_id: int):
    return db.query(models.Appointment).filter(models.Appointment.veterinarian_id == vet_id).all()

def get_appointments_by_vet_and_date(db: Session, vet_id: int, date: date):
     return db.query(models.Appointment).filter(
        models.Appointment.veterinarian_id == vet_id,
        func.date(models.Appointment.appointment_date) == date
    ).order_by(models.Appointment.appointment_date).all()


# --- CRUD Owners ---
def get_owner(db: Session, owner_id: int):
    return db.query(models.Owner).options(joinedload(models.Owner.pets)).filter(models.Owner.owner_id == owner_id).first()

def get_owner_by_email(db: Session, email: str):
    return db.query(models.Owner).filter(models.Owner.email == email).first()

def get_owners(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Owner).options(joinedload(models.Owner.pets)).offset(skip).limit(limit).all()

def create_owner(db: Session, owner: schemas.OwnerCreate):
    db_owner = models.Owner(**owner.model_dump())
    db.add(db_owner)
    db.commit()
    db.refresh(db_owner)
    return db_owner

def update_owner(db: Session, db_owner: models.Owner, owner_update: schemas.OwnerUpdate):
    db_owner = update_db_item(db_owner, owner_update)
    db.commit()
    db.refresh(db_owner)
    return db_owner

def delete_owner(db: Session, db_owner: models.Owner):
    # Lógica de borrado (ej. no borrar si tiene mascotas)
    if db_owner.pets:
        return None # Indica fallo
    db.delete(db_owner)
    db.commit()
    return db_owner

def get_pets_by_owner(db: Session, owner_id: int):
    return db.query(models.Pet).options(joinedload(models.Pet.owner)).filter(models.Pet.owner_id == owner_id).all()

def get_appointments_by_owner(db: Session, owner_id: int):
    return db.query(models.Appointment).join(models.Pet).filter(models.Pet.owner_id == owner_id).all()


# --- CRUD Pets ---
def get_pet(db: Session, pet_id: int):
    return db.query(models.Pet).options(joinedload(models.Pet.owner)).filter(models.Pet.pet_id == pet_id).first()

def get_pets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Pet).options(joinedload(models.Pet.owner)).offset(skip).limit(limit).all()

def create_pet(db: Session, pet: schemas.PetCreate):
    db_pet = models.Pet(**pet.model_dump())
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet

def update_pet(db: Session, db_pet: models.Pet, pet_update: schemas.PetUpdate):
    db_pet = update_db_item(db_pet, pet_update)
    db.commit()
    db.refresh(db_pet)
    return db_pet

def delete_pet(db: Session, db_pet: models.Pet):
    # Lógica de borrado (ej. no borrar si tiene citas activas)
    active_appointments = db.query(models.Appointment).filter(
        models.Appointment.pet_id == db_pet.pet_id,
        models.Appointment.status == 'scheduled'
    ).count()
    if active_appointments > 0:
        return None # Indica fallo
    db.delete(db_pet)
    db.commit()
    return db_pet


# --- CRUD Appointments ---
def get_appointment(db: Session, appt_id: int):
    return db.query(models.Appointment).options(
        joinedload(models.Appointment.pet),
        joinedload(models.Appointment.veterinarian),
        joinedload(models.Appointment.invoice),
        joinedload(models.Appointment.medical_record)
    ).filter(models.Appointment.appointment_id == appt_id).first()

def get_appointments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Appointment).options(
        joinedload(models.Appointment.pet),
        joinedload(models.Appointment.veterinarian)
    ).order_by(models.Appointment.appointment_date.desc()).offset(skip).limit(limit).all()

def create_appointment(db: Session, appt: schemas.AppointmentCreate):
    """Crea una nueva cita y actualiza las métricas (M5)."""
    db_pet = get_pet(db, pet_id=appt.pet_id)
    db_vet = get_veterinarian(db, vet_id=appt.veterinarian_id)
    
    if not db_pet or not db_vet:
        return None 

    db_appt = models.Appointment(**appt.model_dump())
    
    # --- LÓGICA M5 ---
    db_pet.visit_count += 1
    db_pet.last_visit_date = appt.appointment_date.date()
    db_vet.total_appointments += 1
    
    db.add(db_appt)
    db.add(db_pet)
    db.add(db_vet)
    # -----------------
    
    db.commit()
    db.refresh(db_appt)
    return db_appt

def update_appointment(db: Session, db_appt: models.Appointment, appt_update: schemas.AppointmentUpdate):
    db_appt = update_db_item(db_appt, appt_update)
    db.commit()
    db.refresh(db_appt)
    return db_appt

def delete_appointment(db: Session, db_appt: models.Appointment):
    """Borra una cita y revierte las métricas (M5)."""
    db_pet = db_appt.pet
    db_vet = db_appt.veterinarian
    
    # --- LÓGICA M5 ---
    if db_pet:
        db_pet.visit_count = max(0, db_pet.visit_count - 1)
        db.add(db_pet)
    if db_vet:
        db_vet.total_appointments = max(0, db_vet.total_appointments - 1)
        db.add(db_vet)
    # -----------------

    db.delete(db_appt)
    db.commit()
    return db_appt

def get_appointments_by_status_or_date(db: Session, status: str = None, date: date = None):
    query = db.query(models.Appointment)
    if status:
        query = query.filter(models.Appointment.status == status)
    if date:
        query = query.filter(func.date(models.Appointment.appointment_date) == date)
    return query.all()

# --- CRUD Medical Records (M1) ---
def get_medical_record(db: Session, record_id: int):
    return db.query(models.MedicalRecord).filter(models.MedicalRecord.record_id == record_id).first()

def get_medical_record_by_appointment(db: Session, appointment_id: int):
    return db.query(models.MedicalRecord).filter(models.MedicalRecord.appointment_id == appointment_id).first()

def get_medical_records_by_pet(db: Session, pet_id: int):
    return db.query(models.MedicalRecord).join(models.Appointment).filter(models.Appointment.pet_id == pet_id).order_by(models.MedicalRecord.created_at.desc()).all()

def create_medical_record(db: Session, record: schemas.MedicalRecordCreate):
    db_record = models.MedicalRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

def update_medical_record(db: Session, db_record: models.MedicalRecord, record_update: schemas.MedicalRecordUpdate):
    db_record = update_db_item(db_record, record_update)
    db.commit()
    db.refresh(db_record)
    return db_record

# --- CRUD Vaccines (M2) ---
def get_vaccine(db: Session, vaccine_id: int):
    return db.query(models.Vaccine).filter(models.Vaccine.vaccine_id == vaccine_id).first()

def get_vaccine_by_name(db: Session, name: str):
    return db.query(models.Vaccine).filter(models.Vaccine.name == name).first()

def get_vaccines(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vaccine).offset(skip).limit(limit).all()

def create_vaccine(db: Session, vaccine: schemas.VaccineCreate):
    db_vaccine = models.Vaccine(**vaccine.model_dump())
    db.add(db_vaccine)
    db.commit()
    db.refresh(db_vaccine)
    return db_vaccine

# --- CRUD Vaccination Records (M2) ---
def get_vaccination_record(db: Session, record_id: int):
    return db.query(models.VaccinationRecord).options(
        joinedload(models.VaccinationRecord.pet),
        joinedload(models.VaccinationRecord.vaccine),
        joinedload(models.VaccinationRecord.veterinarian)
    ).filter(models.VaccinationRecord.vaccination_id == record_id).first()

def get_vaccination_records(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.VaccinationRecord).options(
        joinedload(models.VaccinationRecord.pet),
        joinedload(models.VaccinationRecord.vaccine),
        joinedload(models.VaccinationRecord.veterinarian)
    ).offset(skip).limit(limit).all()

def create_vaccination_record(db: Session, record: schemas.VaccinationRecordCreate):
    db_record = models.VaccinationRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

def get_vaccinations_by_pet(db: Session, pet_id: int):
    return db.query(models.VaccinationRecord).options(
        joinedload(models.VaccinationRecord.vaccine),
        joinedload(models.VaccinationRecord.veterinarian)
    ).filter(models.VaccinationRecord.pet_id == pet_id).order_by(models.VaccinationRecord.vaccination_date.desc()).all()

def get_vaccination_schedule_by_pet(db: Session, pet_id: int):
    today = date.today()
    return db.query(models.VaccinationRecord).options(
        joinedload(models.VaccinationRecord.vaccine)
    ).filter(
        models.VaccinationRecord.pet_id == pet_id,
        models.VaccinationRecord.next_dose_date >= today
    ).order_by(models.VaccinationRecord.next_dose_date.asc()).all()

# --- CRUD Invoices (M4) ---
def get_invoice(db: Session, invoice_id: int):
    return db.query(models.Invoice).options(
        joinedload(models.Invoice.appointment).joinedload(models.Appointment.pet)
    ).filter(models.Invoice.invoice_id == invoice_id).first()

def get_invoices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Invoice).options(
        joinedload(models.Invoice.appointment).joinedload(models.Appointment.pet)
    ).order_by(models.Invoice.issue_date.desc()).offset(skip).limit(limit).all()

def get_pending_invoices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Invoice).filter(
        models.Invoice.payment_status.in_(['pending', 'overdue'])
    ).order_by(models.Invoice.issue_date.desc()).offset(skip).limit(limit).all()

def mark_invoice_as_paid(db: Session, db_invoice: models.Invoice):
    db_invoice.payment_status = 'paid'
    db_invoice.payment_date = datetime.now()
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

# --- CRUD Reports (M5) ---
def get_revenue_report(db: Session, start_date: date, end_date: date):
    # Suma el total_amount de las facturas pagadas en el rango de fechas
    total_revenue = db.query(func.sum(models.Invoice.total_amount)).filter(
        models.Invoice.payment_status == 'paid',
        models.Invoice.payment_date.between(start_date, end_date)
    ).scalar()
    return total_revenue or Decimal('0.00')

def get_popular_veterinarians(db: Session, limit: int = 5):
    # Reutiliza el contador 'total_appointments' que ya calculamos
    return db.query(models.Veterinarian).order_by(
        models.Veterinarian.total_appointments.desc()
    ).limit(limit).all()

def get_vaccination_alerts(db: Session, days_window: int = 30):
    # Busca vacunas cuya 'next_dose_date' esté en los próximos 30 días
    today = date.today()
    end_date = today + timedelta(days=days_window)
    return db.query(models.VaccinationRecord).options(
        joinedload(models.VaccinationRecord.pet),
        joinedload(models.VaccinationRecord.vaccine)
    ).filter(
        models.VaccinationRecord.next_dose_date.between(today, end_date)
    ).order_by(models.VaccinationRecord.next_dose_date.asc()).all()