"""Test concurrencia de códigos de transferencia con SEQUENCE"""
import pytest
from sqlmodel import Session, select
from concurrent.futures import ThreadPoolExecutor
import threading

from app.core.database import engine
from app.models.transfer import MaterialTransfer, MaterialTransferBatch
from app.models.material import Material, MaterialLot
from app.models.storage import Almacen, Locacion
from app.models.user import User


def test_concurrent_transfer_code_generation():
    """
    Verifica que múltiples transacciones concurrentes generen códigos únicos sin duplicados.
    Esto valida que la SEQUENCE en BD evita race conditions.
    """
    from sqlmodel import create_engine, Session
    
    # Usar la misma BD configurada
    from app.core.database import get_session, engine as db_engine
    
    # Preparar datos base
    with Session(db_engine) as session:
        # Limpiar datos previos de test
        session.exec(select(MaterialTransfer)).all()  # Just check if table exists
        
        # Crear usuario, almacenes y lotes para test
        user = User(
            email=f"test_transfer_{threading.current_thread().ident}@test.com",
            full_name="Test User",
            hashed_password="fake",
            role="almacen",
        )
        session.add(user)
        session.flush()
        
        almacen_src = Almacen(codigo="ALM-SRC-TEST", nombre="Almacen Source Test", activo=True)
        almacen_dst = Almacen(codigo="ALM-DST-TEST", nombre="Almacen Dest Test", activo=True)
        session.add(almacen_src)
        session.add(almacen_dst)
        session.flush()
        
        loc_src = Locacion(
            almacen_id=almacen_src.id,
            codigo="LOC-SRC",
            nombre="Locacion Source",
            activo=True,
        )
        loc_dst = Locacion(
            almacen_id=almacen_dst.id,
            codigo="LOC-DST",
            nombre="Locacion Dest",
            activo=True,
        )
        session.add(loc_src)
        session.add(loc_dst)
        session.flush()
        
        material = Material(
            codigo="MAT-TEST-001",
            nombre="Material Test",
            unidad="kg",
            stock_minimo=0.0,
        )
        session.add(material)
        session.flush()
        
        source_lot = MaterialLot(
            material_id=material.id,
            codigo_lote="TEST-LOT-SOURCE",
            cantidad=1000.0,
            cantidad_reservada=0.0,
            almacen_id=almacen_src.id,
            locacion_id=loc_src.id,
        )
        session.add(source_lot)
        session.commit()
    
    # Función para crear transferencia en thread separado
    created_codes = []
    lock = threading.Lock()
    
    def create_transfer_concurrent(index):
        from sqlmodel import Session as SqlSession
        with SqlSession(db_engine) as session:
            source_lot_db = session.exec(
                select(MaterialLot).where(MaterialLot.codigo_lote == "TEST-LOT-SOURCE")
            ).first()
            
            material_db = session.exec(
                select(Material).where(Material.codigo == "MAT-TEST-001")
            ).first()
            
            almacen_dst_db = session.exec(
                select(Almacen).where(Almacen.codigo == "ALM-DST-TEST")
            ).first()
            
            user_db = session.exec(
                select(User).where(User.email.contains("test_transfer_"))
            ).first()
            
            # Crear transferencia
            transfer = MaterialTransfer(
                material_id=material_db.id,
                source_lot_id=source_lot_db.id,
                destination_lot_id=0,  # Será actualizado
                destination_almacen_id=almacen_dst_db.id,
                quantity=10.0,
                user_id=user_db.id,
            )
            session.add(transfer)
            session.flush()  # Aquí se genera el código
            
            codigo = transfer.codigo
            with lock:
                created_codes.append(codigo)
            
            session.commit()
    
    # Ejecutar 10 transacciones concurrentes
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_transfer_concurrent, i) for i in range(10)]
        for future in futures:
            future.result()
    
    # Verificar que todos los códigos son únicos
    assert len(created_codes) == 10, f"Se esperaban 10 códigos, se obtuvieron {len(created_codes)}"
    assert len(set(created_codes)) == 10, f"Hay códigos duplicados: {created_codes}"
    
    # Verificar que siguen el patrón TR-XXXXXX
    for codigo in created_codes:
        assert codigo.startswith("TR-"), f"Código no comienza con 'TR-': {codigo}"
        assert len(codigo) == 9, f"Código tiene longitud incorrecta: {codigo}"  # TR-000001 = 9 chars
    
    print(f"✅ Test exitoso: Se generaron {len(created_codes)} códigos únicos")
    print(f"Códigos generados: {sorted(created_codes)}")


if __name__ == "__main__":
    test_concurrent_transfer_code_generation()
