import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app.database import SessionLocal, engine
# --- AÑADIR 'auth' PARA HASHEAR CONTRASEÑAS ---
from app import auth 

# ¡Importante! Este script asume que todas las migraciones (M1-M6)
# ya han sido aplicadas con 'alembic upgrade head'.

fake = Faker()
db: Session = SessionLocal()

try:
    print("Iniciando población completa de la base de datos (Post-Migraciones M6)...")

    # --- 1. Crear Veterinarios (con campos M5 y M6) ---
    print("Creando veterinarios...")
    vets = []
    
    # --- LÓGICA DE CONTRASEÑA AÑADIDA ---
    default_password_plain = "admin123"
    default_hashed_password = auth.get_password_hash(default_password_plain)
    print(f"Usando contraseña por defecto hasheada para todos los veterinarios: {default_password_plain}")
    # -----------------------------------

    for _ in range(10):
        vet = models.Veterinarian(
            license_number=fake.unique.bothify(text='VET-#####-??'),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.email(),
            
            # --- AÑADIR ESTE CAMPO OBLIGATORIO ---
            hashed_password=default_hashed_password,
            # ------------------------------------

            phone=fake.phone_number()[:50],
            specialization=random.choice(['Cirugía', 'Dermatología', 'Medicina Interna', 'Oncología', 'General']),
            hire_date=fake.date_between(start_date='-5y', end_date='today'),
            is_active=True,
            consultation_fee=Decimal(random.uniform(50.0, 150.0)).quantize(Decimal('0.01')),
            rating=Decimal(random.uniform(3.0, 5.0)).quantize(Decimal('0.01'))
            # total_appointments se calculará después
        )
        vets.append(vet)
    db.add_all(vets)
    db.commit()
    for v in vets: db.refresh(v)
    print(f"{len(vets)} veterinarios creados.")
    vet_ids = [v.veterinarian_id for v in vets]

    # --- 2. Crear Dueños (con campos M3) ---
    print("Creando dueños...")
    owners = []
    for _ in range(20):
        owner = models.Owner(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:50],
            address=fake.address(),
            emergency_contact=fake.phone_number()[:50],
            preferred_payment_method=random.choice(['cash', 'credit', 'debit', 'insurance'])
        )
        owners.append(owner)
    db.add_all(owners)
    db.commit()
    for o in owners: db.refresh(o)
    print(f"{len(owners)} dueños creados.")
    owner_ids = [o.owner_id for o in owners]

    # --- 3. Crear Mascotas (con campos M3 y M5) ---
    print("Creando mascotas...")
    pets = []
    for _ in range(30):
        pet = models.Pet(
            name=fake.first_name(),
            species=random.choice(['dog', 'cat', 'bird', 'rabbit', 'other']),
            breed=random.choice(['Labrador', 'Siamese', 'Parakeet', 'Angora', 'Mixto', 'N/A']),
            birth_date=fake.date_of_birth(minimum_age=0, maximum_age=15),
            weight=Decimal(random.uniform(0.5, 40.0)).quantize(Decimal('0.01')),
            owner_id=random.choice(owner_ids),
            microchip_number=fake.unique.bothify(text='CHIP-#########'),
            is_neutered=random.choice([True, False]),
            blood_type=random.choice(['DEA 1.1', 'A', 'B', 'AB', None])
            # visit_count y last_visit_date se calcularán después
        )
        pets.append(pet)
    db.add_all(pets)
    db.commit()
    for p in pets: db.refresh(p)
    print(f"{len(pets)} mascotas creadas.")
    pet_ids = [p.pet_id for p in pets]

    # --- 4. Crear Catálogo de Vacunas (M2) ---
    print("Creando catálogo de vacunas...")
    vaccines_data = [
        {"name": "Rabia", "manufacturer": "VetPharm", "species_applicable": "dog,cat"},
        {"name": "Moquillo Canino", "manufacturer": "BioPet", "species_applicable": "dog"},
        {"name": "Parvovirus", "manufacturer": "BioPet", "species_applicable": "dog"},
        {"name": "Triple Felina (FVRCP)", "manufacturer": "CatVax", "species_applicable": "cat"},
    ]
    vaccines = [models.Vaccine(**data) for data in vaccines_data]
    db.add_all(vaccines)
    db.commit()
    for v in vaccines: db.refresh(v)
    print(f"{len(vaccines)} tipos de vacunas creados.")
    vaccine_ids = [v.vaccine_id for v in vaccines]

    # --- 5. Crear Citas (v1.0 y M6) ---
    print("Creando citas...")
    appointments = []
    for _ in range(50):
        # Lógica M6: 1 de cada 10 citas será de emergencia (sin pet_id)
        pet_id_or_none = random.choice(pet_ids) if random.randint(1, 10) != 1 else None
        
        appt = models.Appointment(
            pet_id=pet_id_or_none,
            veterinarian_id=random.choice(vet_ids),
            appointment_date=fake.date_time_between(start_date='-2y', end_date='+1m'),
            reason=fake.sentence(nb_words=5),
            status=random.choice(['scheduled', 'completed', 'cancelled', 'no_show']),
            notes=fake.paragraph(nb_sentences=2)
        )
        appointments.append(appt)
    db.add_all(appointments)
    db.commit()
    for a in appointments: db.refresh(a)
    print(f"{len(appointments)} citas creadas.")

    # --- 6. Crear Historiales Médicos y Facturas (M1, M4) ---
    print("Generando historiales médicos y facturas para citas completadas...")
    medical_records = []
    invoices = []
    completed_appts = [a for a in appointments if a.status == 'completed']
    
    for appt in completed_appts:
        # Crear Historial Médico (M1)
        record = models.MedicalRecord(
            appointment_id=appt.appointment_id,
            diagnosis=f"Diagnóstico: {fake.bs()}",
            treatment=f"Tratamiento: {fake.bs()}",
            prescription=fake.text(max_nb_chars=100),
            follow_up_required=random.choice([True, False])
        )
        medical_records.append(record)
        
        # Crear Factura (M4)
        subtotal = Decimal(random.uniform(50.0, 500.0)).quantize(Decimal('0.01'))
        tax = subtotal * Decimal('0.13') # 13% de impuesto (ejemplo)
        total = subtotal + tax
        
        invoice = models.Invoice(
            appointment_id=appt.appointment_id,
            invoice_number=fake.unique.bothify(text='INV-####-????'),
            issue_date=appt.appointment_date.date(),
            subtotal=subtotal,
            tax_amount=tax.quantize(Decimal('0.01')),
            total_amount=total.quantize(Decimal('0.01')),
            payment_status=random.choice(['paid', 'pending']),
            payment_date=appt.appointment_date if random.choice([True, False]) else None
        )
        invoices.append(invoice)

    db.add_all(medical_records)
    db.add_all(invoices)
    db.commit()
    print(f"{len(medical_records)} historiales médicos creados.")
    print(f"{len(invoices)} facturas creadas.")

    # --- 7. Crear Registros de Vacunación (M2) ---
    print("Creando registros de vacunación...")
    vaccination_records = []
    for pet in pets:
        if random.choice([True, False]): # No todas las mascotas tienen vacunas
            for _ in range(random.randint(1, 3)): # De 1 a 3 vacunas por mascota
                vaccination_records.append(models.VaccinationRecord(
                    pet_id=pet.pet_id,
                    vaccine_id=random.choice(vaccine_ids),
                    veterinarian_id=random.choice(vet_ids),
                    vaccination_date=fake.date_between(start_date='-2y', end_date='today'),
                    next_dose_date=fake.date_between(start_date='+6m', end_date='+1y'),
                    batch_number=fake.bothify(text='B-#####')
                ))
    db.add_all(vaccination_records)
    db.commit()
    print(f"{len(vaccination_records)} registros de vacunación creados.")

    # --- 8. Calcular y Actualizar Métricas (M5) ---
    print("Calculando y actualizando métricas (M5)...")
    
    # Actualizar Pets
    pets_to_update = db.query(models.Pet).all()
    for pet in pets_to_update:
        # Contar citas completadas
        completed_visits = db.query(models.Appointment).filter(
            models.Appointment.pet_id == pet.pet_id,
            models.Appointment.status == 'completed'
        ).count()
        
        # Obtener última visita (completada)
        last_visit = db.query(func.max(models.Appointment.appointment_date)).filter(
            models.Appointment.pet_id == pet.pet_id,
            models.Appointment.status == 'completed'
        ).scalar()
        
        pet.visit_count = completed_visits
        pet.last_visit_date = last_visit.date() if last_visit else None
        db.add(pet)

    # Actualizar Veterinarios
    vets_to_update = db.query(models.Veterinarian).all()
    for vet in vets_to_update:
        # Contar todas sus citas
        total_appts = db.query(models.Appointment).filter(
            models.Appointment.veterinarian_id == vet.veterinarian_id
        ).count()
        
        vet.total_appointments = total_appts
        db.add(vet)

    db.commit()
    print("Métricas de mascotas y veterinarios actualizadas.")
    
    print("\n--- ¡POBLACIÓN COMPLETA FINALIZADA! ---")

except Exception as e:
    print(f"\n--- ERROR DURANTE LA POBLACIÓN ---")
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
    print("Sesión de base de datos cerrada.")