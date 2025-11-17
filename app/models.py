from sqlalchemy import (Column, Integer, String, Text, Date, TIMESTAMP, Numeric,
                        Boolean, ForeignKey, Enum)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Veterinarian(Base):
    __tablename__ = "veterinarians"
    
    veterinarian_id = Column(Integer, primary_key=True, index=True)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    #--- ESTA LÍNEA (M6: Auth) ---
    hashed_password = Column(String(255), nullable=True)

    phone = Column(String(30))
    specialization = Column(String(200))
    hire_date = Column(Date, nullable=False, default=func.current_date())
    is_active = Column(Boolean, default=True)

    # --- ESTAS LÍNEAS (M5) ---
    consultation_fee = Column(Numeric(8, 2), nullable=True) # Tarifa por consulta
    rating = Column(Numeric(3, 2), nullable=True) # Calificación promedio
    total_appointments = Column(Integer, nullable=False, default=0) # Contador de citas
    
    # Relación: Un veterinario tiene muchas citas
    appointments = relationship("Appointment", back_populates="veterinarian")

    # Relación: Un veterinario puede tener muchos registros de vacunación
    vaccination_records = relationship("VaccinationRecord", back_populates="veterinarian")

class Owner(Base):
    __tablename__ = "owners"
    
    owner_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(30))
    address = Column(Text)
    registration_date = Column(TIMESTAMP, server_default=func.now())

    # --- ESTAS LÍNEAS (MIGRACIÓN 3) ---
    emergency_contact = Column(String(30), nullable=True) 
    preferred_payment_method = Column(Enum('cash', 'credit', 'debit', 'insurance', name='payment_method_enum'), nullable=True)
    
    # Relación: Un dueño tiene muchas mascotas
    pets = relationship("Pet", back_populates="owner")

class Pet(Base):
    __tablename__ = "pets"
    
    pet_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    species = Column(Enum('dog', 'cat', 'bird', 'rabbit', 'other', name='species_enum'), nullable=False)
    breed = Column(String(100))
    birth_date = Column(Date, nullable=True)
    weight = Column(Numeric(6, 2))
    
    # Foreign Key
    owner_id = Column(Integer, ForeignKey("owners.owner_id"), nullable=False) 
    registration_date = Column(TIMESTAMP, server_default=func.now())
    
    # --- ESTAS LÍNEAS (M5) ---
    last_visit_date = Column(Date, nullable=True) # Fecha de última visita
    visit_count = Column(Integer, nullable=False, default=0) # Contador de visitas

# --- ESTAS LÍNEAS (MIGRACIÓN 3) ---
    microchip_number = Column(String(50), unique=True, nullable=True, index=True)
    is_neutered = Column(Boolean, default=False)
    blood_type = Column(String(10), nullable=True)

    # Relaciones inversas
    owner = relationship("Owner", back_populates="pets")
    appointments = relationship("Appointment", back_populates="pet")
    # Relación: Una mascota puede tener muchos registros de vacunación
    vaccination_records = relationship("VaccinationRecord", back_populates="pet", cascade="all, delete-orphan")

class Appointment(Base):
    __tablename__ = "appointments"
    
    appointment_id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    pet_id = Column(Integer, ForeignKey("pets.pet_id"), nullable=True)
    veterinarian_id = Column(Integer, ForeignKey("veterinarians.veterinarian_id"), nullable=False)
    
    appointment_date = Column(TIMESTAMP, nullable=False)
    reason = Column(Text)
    status = Column(Enum('scheduled', 'completed', 'cancelled', 'no_show', name='appointment_status_enum'), default='scheduled')
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relaciones inversas
    pet = relationship("Pet", back_populates="appointments")
    veterinarian = relationship("Veterinarian", back_populates="appointments")
    medical_record = relationship("MedicalRecord", uselist=False, back_populates="appointment", cascade="all, delete-orphan")

    # --- ESTA LÍNEA (M4) ---
    invoice = relationship("Invoice", uselist=False, back_populates="appointment", cascade="all, delete-orphan")

    # 'uselist=False' es clave para 1:1
    # 'cascade="all, delete-orphan"' asegura que si borras la cita, se borra el historial
    #  o si quitas el historial de la cita, se borra el historial.

class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    record_id = Column(Integer, primary_key=True, index=True)
    
    # FK con UNIQUE = True para enforce una relación 1:1 con Appointment
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id", ondelete="CASCADE"), unique=True, nullable=False)
    
    diagnosis = Column(Text, nullable=False)
    treatment = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True) # Puede ser nulo
    follow_up_required = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relación inversa con Appointment
    appointment = relationship("Appointment", back_populates="medical_record")


class Vaccine(Base):
    """
    Tabla de tipos de vacunas (ej. Rabia, Moquillo)
    """
    __tablename__ = "vaccines"
    
    vaccine_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    manufacturer = Column(String(200))
    species_applicable = Column(String(100)) # ej. 'dog', 'cat', 'dog,cat'
    
    # Relación inversa: Una vacuna está en muchos registros
    vaccination_records = relationship("VaccinationRecord", back_populates="vaccine")

class VaccinationRecord(Base):
    """
    Tabla de registro de vacunas aplicadas a mascotas
    """
    __tablename__ = "vaccination_records"
    
    vaccination_id = Column(Integer, primary_key=True, index=True)
    
    # Claves Foráneas
    pet_id = Column(Integer, ForeignKey("pets.pet_id", ondelete="CASCADE"), nullable=False)
    vaccine_id = Column(Integer, ForeignKey("vaccines.vaccine_id"), nullable=False)
    veterinarian_id = Column(Integer, ForeignKey("veterinarians.veterinarian_id"), nullable=False)
    
    vaccination_date = Column(Date, nullable=False, default=func.current_date())
    next_dose_date = Column(Date, nullable=True) # Opcional
    batch_number = Column(String(50)) # Número de lote de la vacuna
    
    # Relaciones inversas
    pet = relationship("Pet", back_populates="vaccination_records")
    vaccine = relationship("Vaccine", back_populates="vaccination_records")
    veterinarian = relationship("Veterinarian", back_populates="vaccination_records")


# --- CLASE NUEVA (M4) ---
class Invoice(Base):
    __tablename__ = "invoices"
    
    invoice_id = Column(Integer, primary_key=True, index=True)
    
    # Clave foránea única para la relación 1:1
    appointment_id = Column(Integer, ForeignKey("appointments.appointment_id", ondelete="SET NULL"), unique=True, nullable=True)
    
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    issue_date = Column(Date, nullable=False, default=func.current_date())
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    payment_status = Column(Enum('pending', 'partial', 'paid', 'overdue', name='invoice_payment_status_enum'), default='pending')
    payment_date = Column(TIMESTAMP, nullable=True) # Se llena cuando 'status' es 'paid'
    
    # Relación inversa
    appointment = relationship("Appointment", back_populates="invoice")