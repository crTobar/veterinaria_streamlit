from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

# --- Enums v1.0 ---
class SpeciesEnum(str, Enum):
    dog = 'dog'
    cat = 'cat'
    bird = 'bird'
    rabbit = 'rabbit'
    other = 'other'

class AppointmentStatusEnum(str, Enum):
    scheduled = 'scheduled'
    completed = 'completed'
    cancelled = 'cancelled'
    no_show = 'no_show'

# --- Enums (Migraciones) ---
class PaymentMethodEnum(str, Enum):
    cash = 'cash'
    credit = 'credit'
    debit = 'debit'
    insurance = 'insurance'

class InvoicePaymentStatusEnum(str, Enum):
    pending = 'pending'
    partial = 'partial'
    paid = 'paid'
    overdue = 'overdue'

# --- Schemas Simplificados (para anidación) ---

class PetSimple(BaseModel):
    pet_id: int
    name: str
    species: SpeciesEnum
    class Config:
        from_attributes = True

class OwnerSimple(BaseModel):
    owner_id: int
    first_name: str
    last_name: str
    email: EmailStr
    class Config:
        from_attributes = True

class VeterinarianSimple(BaseModel):
    veterinarian_id: int
    first_name: str
    last_name: str
    specialization: Optional[str] = None
    class Config:
        from_attributes = True

# --- Veterinarians ---
class VeterinarianBase(BaseModel):
    license_number: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    specialization: Optional[str] = Field(None, max_length=200)
    hire_date: Optional[date] = None
    is_active: bool = True
    # --- M5 ---
    consultation_fee: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    rating: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)

class VeterinarianCreate(VeterinarianBase):
    password: str
    pass

class VeterinarianUpdate(BaseModel):
    license_number: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    specialization: Optional[str] = Field(None, max_length=200)
    hire_date: Optional[date] = None
    is_active: Optional[bool] = None
    # --- M5 ---
    consultation_fee: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    rating: Optional[Decimal] = Field(None, ge=0, le=5, decimal_places=2)

class Veterinarian(VeterinarianBase):
    veterinarian_id: int
    # --- M5 ---
    total_appointments: int
    class Config:
        from_attributes = True

# --- Owners ---
class OwnerBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    # --- M3 ---
    emergency_contact: Optional[str] = Field(None, max_length=50)
    preferred_payment_method: Optional[PaymentMethodEnum] = None

class OwnerCreate(OwnerBase):
    pass

class OwnerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    # --- M3 ---
    emergency_contact: Optional[str] = Field(None, max_length=50)
    preferred_payment_method: Optional[PaymentMethodEnum] = None

class Owner(OwnerBase):
    owner_id: int
    registration_date: datetime
    pets: List[PetSimple] = []
    class Config:
        from_attributes = True

# --- Pets ---
class PetBase(BaseModel):
    name: str = Field(..., max_length=100)
    species: SpeciesEnum
    breed: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    weight: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    owner_id: int
    # --- M3 ---
    microchip_number: Optional[str] = Field(None, max_length=50, unique=True)
    is_neutered: bool = False
    blood_type: Optional[str] = Field(None, max_length=10)

class PetCreate(PetBase):
    pass

class PetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    species: Optional[SpeciesEnum] = None
    breed: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    weight: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    owner_id: Optional[int] = None
    # --- M3 ---
    microchip_number: Optional[str] = Field(None, max_length=50, unique=True)
    is_neutered: Optional[bool] = None
    blood_type: Optional[str] = Field(None, max_length=10)

class Pet(PetBase):
    pet_id: int
    registration_date: datetime
    owner: OwnerSimple
    # --- M5 ---
    last_visit_date: Optional[date] = None
    visit_count: int
    class Config:
        from_attributes = True

# --- Appointments ---
class AppointmentBase(BaseModel):
    pet_id: int
    veterinarian_id: int
    appointment_date: datetime
    reason: Optional[str] = None
    status: Optional[AppointmentStatusEnum] = AppointmentStatusEnum.scheduled
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    pet_id: Optional[int] = None
    veterinarian_id: Optional[int] = None
    appointment_date: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[AppointmentStatusEnum] = None
    notes: Optional[str] = None

class Appointment(AppointmentBase):
    appointment_id: int
    created_at: datetime
    pet: PetSimple
    veterinarian: VeterinarianSimple
    # 'invoice' se añade más abajo para evitar error de referencia
    
    class Config:
        from_attributes = True

# --- Medical Records (M1) ---
class MedicalRecordBase(BaseModel):
    appointment_id: int
    diagnosis: str
    treatment: str
    prescription: Optional[str] = None
    follow_up_required: bool = False

class MedicalRecordCreate(MedicalRecordBase):
    pass

class MedicalRecordUpdate(BaseModel):
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    prescription: Optional[str] = None
    follow_up_required: Optional[bool] = None

class MedicalRecord(MedicalRecordBase):
    record_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Vaccines (M2) ---
class VaccineBase(BaseModel):
    name: str = Field(..., max_length=200)
    manufacturer: Optional[str] = Field(None, max_length=200)
    species_applicable: Optional[str] = Field(None, max_length=100)

class VaccineCreate(VaccineBase):
    pass

class Vaccine(VaccineBase):
    vaccine_id: int
    class Config:
        from_attributes = True

# --- Vaccination Records (M2) ---
class VaccinationRecordBase(BaseModel):
    pet_id: int
    vaccine_id: int
    veterinarian_id: int
    vaccination_date: date
    next_dose_date: Optional[date] = None
    batch_number: Optional[str] = Field(None, max_length=50)

class VaccinationRecordCreate(VaccinationRecordBase):
    pass

class VaccinationRecord(VaccinationRecordBase):
    vaccination_id: int
    pet: PetSimple 
    vaccine: Vaccine
    veterinarian: VeterinarianSimple 
    class Config:
        from_attributes = True

# --- Invoices (M4) ---
class InvoiceBase(BaseModel):
    appointment_id: Optional[int] = None
    invoice_number: str = Field(..., max_length=50)
    issue_date: date
    subtotal: Decimal
    tax_amount: Decimal = Field(default=0.00)
    total_amount: Decimal
    payment_status: InvoicePaymentStatusEnum = InvoicePaymentStatusEnum.pending
    payment_date: Optional[datetime] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    payment_status: InvoicePaymentStatusEnum

class Invoice(InvoiceBase):
    invoice_id: int
    appointment: Optional[Appointment] = None 
    class Config:
        from_attributes = True

# --- Schemas de Reportes (M5) ---

class RevenueReport(BaseModel):
    start_date: date
    end_date: date
    total_revenue: Decimal

class PopularVeterinarianReport(BaseModel):
    veterinarian: VeterinarianSimple
    appointment_count: int

class VaccinationAlertReport(BaseModel):
    pet: PetSimple
    vaccine: Vaccine
    next_dose_date: date

class Token(BaseModel):
    """
    Schema de respuesta cuando el login es exitoso.
    Devuelve el token y el tipo ("bearer").
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Schema para los datos que están DENTRO del token JWT.
    """
    email: Optional[str] = None

class LoginRequest(BaseModel):
    """
    Schema para el body de la petición /login.
    Usa 'username' que será el email del veterinario.
    """
    username: EmailStr
    password: str

class PasswordRecoveryRequest(BaseModel):
    """
    Schema para el body de /recover-password
    """
    email: EmailStr

# --- Reconstrucción de Modelos ---
# (Necesario para que Pydantic maneje las referencias circulares/forward)
Owner.model_rebuild()
Pet.model_rebuild()
Appointment.model_rebuild()
Invoice.model_rebuild()