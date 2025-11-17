"""M6_Agregar_auth_y_citas_de_emergencia (Versión Segura y Estricta)

Revision ID: 0a2f2da6a729
Revises: b9d925015eb2
Create Date: 2025-11-16 19:55:04.552053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
# NO IMPORTAR PASSLIB O BCRYPT AQUÍ ARRIBA

# revision identifiers, used by Alembic.
revision: str = '0a2f2da6a729'
down_revision: Union[str, Sequence[str], None] = 'b9d925015eb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- Nombres de Tablas de Backup ---
vets_backup_table = f'backup_{revision}_vets_auth'
appts_backup_table = f'backup_{revision}_appts_emergency'


def upgrade() -> None:
    
    # --- LÓGICA DE HASHING MOVIDA DENTRO DE UPGRADE ---
    try:
        from passlib.hash import bcrypt
        default_password_plain = 'admin123'
        default_hashed_password = bcrypt.hash(default_password_plain)
        print("Hash de contraseña por defecto generado exitosamente.")
    except Exception as e:
        # --- CAMBIO IMPORTANTE ---
        # En lugar de continuar con un fallback, detenemos la migración.
        print(f"\n--- ERROR FATAL DE MIGRACIÓN (M6) ---")
        print(f"No se pudo importar 'passlib' o 'bcrypt' para hashear la contraseña.")
        print(f"Error: {e}")
        print("Por favor, soluciona la instalación de la librería ejecutando:")
        print("1. pip uninstall passlib bcrypt")
        print("2. pip install --no-cache-dir \"passlib[bcrypt]\"")
        print("La migración M6 ha sido ABORTADA.")
        # Volver a lanzar la excepción para detener Alembic
        raise e
    # --- FIN DEL CAMBIO ---

    conn = op.get_bind()
    print("M6: Iniciando upgrade...")
    
    # --- 1. Lógica para Appointments (Emergencias) ---
    print("Modificando 'appointments.pet_id' para que sea opcional (nullable=True)...")
    op.alter_column('appointments', 'pet_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # --- 2. Lógica para Veterinarians (Auth) ---
    print("Añadiendo columna 'hashed_password' a 'veterinarians'...")
    op.add_column('veterinarians', sa.Column('hashed_password', sa.String(length=255), nullable=True))

    print(f"Estableciendo contraseña por defecto ('{default_password_plain}') para veterinarios nuevos...")
    op.execute(
        text(f"""
        UPDATE veterinarians
        SET hashed_password = '{default_hashed_password}'
        WHERE hashed_password IS NULL
        """)
    )
    
    op.alter_column('veterinarians', 'hashed_password',
               existing_type=sa.String(length=255),
               nullable=False)
               
    # --- 3. Lógica de Restauración (si venimos de un downgrade) ---
    print("Buscando backups de downgrade anterior...")
    
    result_vets = conn.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{vets_backup_table}')")).scalar()
    if result_vets:
        print(f"Restaurando contraseñas desde {vets_backup_table}...")
        op.execute(f"""
            UPDATE veterinarians v
            SET hashed_password = b.hashed_password
            FROM {vets_backup_table} b
            WHERE v.veterinarian_id = b.veterinarian_id;
            
            DROP TABLE {vets_backup_table};
        """)

    result_appts = conn.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{appts_backup_table}')")).scalar()
    if result_appts:
        print(f"Restaurando citas de emergencia (pet_id=NULL) desde {appts_backup_table}...")
        op.execute(f"""
            UPDATE appointments
            SET pet_id = NULL
            WHERE appointment_id IN (SELECT appointment_id FROM {appts_backup_table});
            
            DROP TABLE {appts_backup_table};
        """)
    
    print("M6: Upgrade completado.")


def downgrade() -> None:
    print("M6: Iniciando downgrade...")
    
    # --- 1. Backup de Veterinarians (Auth) ---
    print(f"Creando backup de contraseñas en {vets_backup_table}...")
    op.execute(f"""
        DROP TABLE IF EXISTS {vets_backup_table};
        CREATE TABLE {vets_backup_table} AS
        SELECT veterinarian_id, hashed_password
        FROM veterinarians;
    """)
    
    # --- 2. Backup y Limpieza de Appointments (Emergencias) ---
    print(f"Creando backup de citas de emergencia (pet_id IS NULL) en {appts_backup_table}...")
    op.execute(f"""
        DROP TABLE IF EXISTS {appts_backup_table};
        CREATE TABLE {appts_backup_table} AS
        SELECT appointment_id
        FROM appointments
        WHERE pet_id IS NULL;
    """)
    
    print("Eliminando citas de emergencia (pet_id IS NULL) para revertir a NOT NULL...")
    op.execute("DELETE FROM appointments WHERE pet_id IS NULL")

    # --- 3. Revertir Esquema ---
    print("Eliminando columna 'hashed_password' de 'veterinarians'...")
    op.drop_column('veterinarians', 'hashed_password')
    
    print("Revirtiendo 'appointments.pet_id' a non-nullable...")
    op.alter_column('appointments', 'pet_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    print("M6: Downgrade completado. Datos preservados en tablas de backup.")