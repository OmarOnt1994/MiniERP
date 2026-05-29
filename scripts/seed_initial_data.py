"""Seed initial data for MiniERP.

Run after migrations are applied:

powershell
python scripts/seed_initial_data.py

"""
from sqlmodel import Session, select
from app.core.database import engine
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import text
from app.models.storage import Almacen, Locacion
from app.models.transfer import MaterialTransfer, MaterialTransferBatch

SEED_PASSWORD = "1234"
SUPERUSER_EMAIL = "admin@mini.erp"
NORMAL_USER_EMAIL = "usuario@mini.erp"


def seed():
    with Session(engine) as session:
        seed_users = [
            {
                "email": SUPERUSER_EMAIL,
                "full_name": "Administrador",
                "role": "admin",
            },
            {
                "email": NORMAL_USER_EMAIL,
                "full_name": "Usuario Normal",
                "role": "lectura",
            },
        ]

        for user_data in seed_users:
            existing = session.exec(select(User).where(User.email == user_data["email"])).first()
            if existing:
                existing.hashed_password = get_password_hash(SEED_PASSWORD)
                existing.full_name = user_data["full_name"]
                existing.role = user_data["role"]
                existing.is_active = True
                session.add(existing)
                print(f"User updated: {user_data['email']} (password set to {SEED_PASSWORD})")
                continue

            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(SEED_PASSWORD),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True,
            )
            session.add(user)

        session.commit()
        print(f"Seed users ready with password: {SEED_PASSWORD}")

    # Crear almacenes/locaciones básicos si no existen
    with Session(engine) as session:
        alm = session.exec(select(Almacen).where(Almacen.codigo == "DEFAULT")).first()
        if not alm:
            almacen = Almacen(codigo="DEFAULT", nombre="Almacen Principal", activo=True)
            session.add(almacen)
            session.flush()
            loc = Locacion(almacen_id=almacen.id, codigo="DEFAULT-LOC", nombre="Ubicación Principal", activo=True)
            session.add(loc)
            session.commit()
            print("Created default almacen and locacion")
        else:
            print("Default almacen already exists")

    # Ajustar sequences para transfer codes (PostgreSQL)
    # Esto evita que la sequence genere valores ya usados si hay datos previos.
    try:
        with engine.connect() as conn:
            # Crear sequences si no existen
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS transfer_code_seq START 1"))
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS transfer_batch_folio_seq START 1"))

            # Obtener max numérico actual para TR-##### y TF-#####
            res = conn.execute(text("SELECT COALESCE(MAX((regexp_replace(codigo, '^TR-',''))::int), 0) as maxv FROM materialtransfer"))
            max_tr = res.scalar() or 0
            if max_tr > 0:
                conn.execute(text("SELECT setval('transfer_code_seq', :v, true)"), {"v": max_tr})
            else:
                conn.execute(text("SELECT setval('transfer_code_seq', 1, false)"))

            res2 = conn.execute(text("SELECT COALESCE(MAX((regexp_replace(folio, '^TF-',''))::int), 0) as maxv FROM materialtransferbatch"))
            max_tf = res2.scalar() or 0
            if max_tf > 0:
                conn.execute(text("SELECT setval('transfer_batch_folio_seq', :v, true)"), {"v": max_tf})
            else:
                conn.execute(text("SELECT setval('transfer_batch_folio_seq', 1, false)"))

            print(f"Adjusted sequences: transfer_code_seq -> {max_tr}, transfer_batch_folio_seq -> {max_tf}")
    except Exception as e:
        print("Warning: could not adjust sequences automatically. Verify DB is PostgreSQL and migrations applied.")
        print("Error:", e)


if __name__ == "__main__":
    seed()
