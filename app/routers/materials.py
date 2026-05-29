from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.material import Material, MaterialLot, InventoryMovement
from app.models.storage import Almacen, Locacion
from app.models.user import User
from app.schemas.material import (
    MaterialCreate, MaterialRead, MaterialUpdate,
    MaterialLotCreate, MaterialLotRead, MaterialLotUpdate,
    MaterialInventorySummary,
    InventoryMovementRead,
    InventoryMovementReportSummary,
    InventoryMovementReportResponse,
)
from app.dependencies.auth import get_current_user, require_roles
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/materials", tags=["materials"])

# ===== MAESTRO DE MATERIALES =====

@router.post("/", response_model=MaterialRead)
def create_material(
    material: MaterialCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen"))
):
    """Crear material (maestro)"""
    # Verificar que no exista un material con el mismo código
    exists = session.exec(select(Material).where(Material.codigo == material.codigo)).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"Ya existe un material con codigo '{material.codigo}'")

    db_material = Material(**material.model_dump())
    session.add(db_material)
    session.commit()
    session.refresh(db_material)
    return db_material

@router.get("/", response_model=list[MaterialRead])
def list_materials(session: Session = Depends(get_session)):
    """Listar materiales (maestro)"""
    return session.exec(select(Material)).all()

@router.get("/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, session: Session = Depends(get_session)):
    """Obtener detalle de material (maestro)"""
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    return material

@router.put("/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: int,
    material_update: MaterialUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen"))
):
    """Actualizar datos del material"""
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    
    material_data = material_update.model_dump(exclude_unset=True)
    # Si se intenta cambiar el codigo, verificar duplicado
    if "codigo" in material_data:
        new_codigo = material_data["codigo"]
        if new_codigo != material.codigo:
            conflict = session.exec(select(Material).where(Material.codigo == new_codigo)).first()
            if conflict:
                raise HTTPException(status_code=400, detail=f"Ya existe un material con codigo '{new_codigo}'")

    for key, value in material_data.items():
        setattr(material, key, value)
    
    session.add(material)
    session.commit()
    session.refresh(material)
    return material

# ===== GESTIÓN DE LOTES =====

@router.post("/{material_id}/lotes", response_model=MaterialLotRead)
def create_material_lot(
    material_id: int,
    lot_data: MaterialLotCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen"))
):
    """
    Registrar entrada de material con lote (FIFO).
    Esto reemplaza el concepto anterior de "entrada" - ahora es por lote.
    """
    # Validar que el material exista
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    
    # Validar que el código de lote sea único por material
    existing = session.exec(
        select(MaterialLot)
        .where(MaterialLot.material_id == material_id)
        .where(MaterialLot.codigo_lote == lot_data.codigo_lote)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Lote '{lot_data.codigo_lote}' ya existe para este material"
        )
    
    # Validar que fecha_caducidad sea en el futuro si se proporciona
    if lot_data.fecha_caducidad and lot_data.fecha_caducidad < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="La fecha de caducidad debe ser futura"
        )
    
    selected_almacen_id = lot_data.almacen_id
    selected_locacion_id = lot_data.locacion_id

    if selected_locacion_id is not None:
        locacion = session.get(Locacion, selected_locacion_id)
        if not locacion:
            raise HTTPException(status_code=404, detail="Locacion no encontrada")
        if selected_almacen_id is not None and locacion.almacen_id != selected_almacen_id:
            raise HTTPException(status_code=400, detail="La locacion no pertenece al almacen indicado")
        selected_almacen_id = locacion.almacen_id

    if selected_almacen_id is not None:
        almacen = session.get(Almacen, selected_almacen_id)
        if not almacen:
            raise HTTPException(status_code=404, detail="Almacen no encontrado")

    # Crear lote
    db_lot = MaterialLot(
        material_id=material_id,
        codigo_lote=lot_data.codigo_lote,
        cantidad=lot_data.cantidad,
        almacen_id=selected_almacen_id,
        locacion_id=selected_locacion_id,
        costo_unitario=lot_data.costo_unitario,
        costo_total=(lot_data.cantidad * lot_data.costo_unitario) if lot_data.costo_unitario else None,
        fecha_caducidad=lot_data.fecha_caducidad,
        notas=lot_data.notas
    )
    session.add(db_lot)
    session.flush()
    session.add(
        InventoryMovement(
            inventory_type="material",
            movement_type="entrada",
            quantity=lot_data.cantidad,
            material_id=material_id,
            material_lot_id=db_lot.id,
            user_id=current_user.id,
            reference_code=lot_data.codigo_lote,
            notes=lot_data.notas,
            unit_cost=lot_data.costo_unitario,
            total_cost=(lot_data.cantidad * lot_data.costo_unitario) if lot_data.costo_unitario else None,
        )
    )
    session.commit()
    session.refresh(db_lot)
    return db_lot

@router.get("/{material_id}/lotes", response_model=list[MaterialLotRead])
def list_material_lots(
    material_id: int,
    session: Session = Depends(get_session)
):
    """
    Listar todos los lotes de un material ordenados por FIFO (fecha_entrada ascendente).
    El primero de la lista es el que se debe usar primero.
    """
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    
    # Ordenar por fecha_entrada (más antiguo primero = FIFO)
    lotes = session.exec(
        select(MaterialLot)
        .where(MaterialLot.material_id == material_id)
        .order_by(MaterialLot.fecha_entrada.asc())
    ).all()
    
    return lotes

@router.get("/{material_id}/inventario", response_model=MaterialInventorySummary)
def get_material_inventory_summary(
    material_id: int,
    session: Session = Depends(get_session)
):
    """
    Resumen completo del inventario de un material:
    - Stock total
    - Cantidad de lotes
    - Lotes proximos a caducar (próximos 30 días)
    - Lotes ya caducados
    - Detalle de todos los lotes ordenados por FIFO
    """
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    
    # Obtener todos los lotes
    lotes = session.exec(
        select(MaterialLot)
        .where(MaterialLot.material_id == material_id)
        .order_by(MaterialLot.fecha_entrada.asc())
    ).all()
    
    # Calcular métricas
    stock_total = sum(lot.cantidad for lot in lotes)
    stock_reservado = sum(lot.cantidad_reservada for lot in lotes)
    stock_disponible = sum(lot.cantidad - lot.cantidad_reservada for lot in lotes)
    
    now = datetime.utcnow()
    proximos_30_dias = now + timedelta(days=30)
    
    proximamente_caduca = sum(
        1 for lot in lotes
        if lot.fecha_caducidad and now < lot.fecha_caducidad <= proximos_30_dias
    )
    
    ya_caducados = sum(
        1 for lot in lotes
        if lot.fecha_caducidad and lot.fecha_caducidad < now
    )
    
    return MaterialInventorySummary(
        material_id=material.id,
        codigo=material.codigo,
        nombre=material.nombre,
        unidad=material.unidad,
        stock_total=stock_total,
        stock_disponible=stock_disponible,
        stock_reservado=stock_reservado,
        cantidad_lotes=len(lotes),
        proximamente_caduca=proximamente_caduca,
        ya_caducados=ya_caducados,
        lotes=[
            MaterialLotRead(
                id=lot.id,
                material_id=lot.material_id,
                codigo_lote=lot.codigo_lote,
                cantidad=lot.cantidad,
                cantidad_reservada=lot.cantidad_reservada,
                cantidad_disponible=lot.cantidad - lot.cantidad_reservada,
                almacen_id=lot.almacen_id,
                locacion_id=lot.locacion_id,
                costo_unitario=lot.costo_unitario,
                costo_total=lot.costo_total,
                fecha_entrada=lot.fecha_entrada,
                fecha_caducidad=lot.fecha_caducidad,
                notas=lot.notas,
                created_at=lot.created_at,
            )
            for lot in lotes
        ]
    )

@router.get("/lotes/caducidad/alertas")
def get_expiry_alerts(session: Session = Depends(get_session)):
    """
    Obtener alertas de caducidad para todos los materiales.
    Muestra lotes que van a caducar en próximos 30 días y ya caducados.
    """
    now = datetime.utcnow()
    proximos_30_dias = now + timedelta(days=30)
    
    # Lotes que van a caducar
    lotes_por_caducar = session.exec(
        select(MaterialLot)
        .where(MaterialLot.fecha_caducidad.isnot(None))
        .where(MaterialLot.fecha_caducidad <= proximos_30_dias)
        .where(MaterialLot.fecha_caducidad > now)
        .order_by(MaterialLot.fecha_caducidad.asc())
    ).all()
    
    # Lotes ya caducados
    lotes_caducados = session.exec(
        select(MaterialLot)
        .where(MaterialLot.fecha_caducidad.isnot(None))
        .where(MaterialLot.fecha_caducidad < now)
        .order_by(MaterialLot.fecha_caducidad.asc())
    ).all()
    
    return {
        "proximos_a_caducar": [
            {
                "lote": lot.codigo_lote,
                "material": session.get(Material, lot.material_id).nombre,
                "cantidad": lot.cantidad,
                "fecha_caducidad": lot.fecha_caducidad,
                "dias_para_caducar": (lot.fecha_caducidad - now).days
            }
            for lot in lotes_por_caducar
        ],
        "ya_caducados": [
            {
                "lote": lot.codigo_lote,
                "material": session.get(Material, lot.material_id).nombre,
                "cantidad": lot.cantidad,
                "fecha_caducidad": lot.fecha_caducidad,
                "dias_caducado": (now - lot.fecha_caducidad).days
            }
            for lot in lotes_caducados
        ]
    }

@router.put("/{material_id}/lotes/{lot_id}", response_model=MaterialLotRead)
def update_material_lot(
    material_id: int,
    lot_id: int,
    lot_update: MaterialLotUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen"))
):
    """Actualizar datos de un lote (cantidad, ubicación, notas, fecha caducidad)"""
    lot = session.get(MaterialLot, lot_id)
    if not lot or lot.material_id != material_id:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    # Si se actualiza fecha_caducidad, validar que sea futura
    if lot_update.fecha_caducidad and lot_update.fecha_caducidad < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="La fecha de caducidad debe ser futura"
        )
    
    lot_data = lot_update.model_dump(exclude_unset=True)

    if "locacion_id" in lot_data and lot_data["locacion_id"] is not None:
        locacion = session.get(Locacion, lot_data["locacion_id"])
        if not locacion:
            raise HTTPException(status_code=404, detail="Locacion no encontrada")
        if "almacen_id" in lot_data and lot_data["almacen_id"] is not None and locacion.almacen_id != lot_data["almacen_id"]:
            raise HTTPException(status_code=400, detail="La locacion no pertenece al almacen indicado")
        lot_data["almacen_id"] = locacion.almacen_id

    if "almacen_id" in lot_data and lot_data["almacen_id"] is not None:
        almacen = session.get(Almacen, lot_data["almacen_id"])
        if not almacen:
            raise HTTPException(status_code=404, detail="Almacen no encontrado")

    for key, value in lot_data.items():
        setattr(lot, key, value)
    
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot

@router.delete("/{material_id}/lotes/{lot_id}")
def delete_material_lot(
    material_id: int,
    lot_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen"))
):
    """Eliminar un lote (usar con cuidado - auditoría recomendada)"""
    lot = session.get(MaterialLot, lot_id)
    if not lot or lot.material_id != material_id:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    session.delete(lot)
    session.commit()
    return {"detail": "Lote eliminado"}

@router.post("/{material_id}/lotes/{lot_id}/usar")
def consume_material_from_lot(
    material_id: int,
    lot_id: int,
    cantidad: float,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion"))
):
    """
    Consumir cantidad de un lote específico.
    Usado internamente por Work Orders para surtir.
    """
    # Lock the lot row to avoid concurrent modifications
    lot = session.exec(
        select(MaterialLot).where(MaterialLot.id == lot_id).with_for_update()
    ).one()
    if not lot or lot.material_id != material_id:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="Cantidad debe ser positiva")
    
    if lot.cantidad < cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Cantidad insuficiente en lote. Disponible: {lot.cantidad}"
        )
    
    lot.cantidad -= cantidad
    session.add(lot)
    session.commit()
    session.refresh(lot)
    # Registrar movimiento de consumo con costos si están disponibles
    material = session.get(Material, material_id)
    unit_cost = lot.costo_unitario
    total_cost = (unit_cost * cantidad) if unit_cost is not None else None

    session.add(
        InventoryMovement(
            inventory_type="material",
            movement_type="consumo",
            quantity=cantidad,
            material_id=material_id,
            material_lot_id=lot.id,
            user_id=current_user.id,
            reference_code=lot.codigo_lote,
            notes="Consumo manual de lote",
            unit_cost=unit_cost,
            total_cost=total_cost,
        )
    )
    session.commit()
    session.refresh(lot)

    return {
        "lote": lot.codigo_lote,
        "cantidad_consumida": cantidad,
        "cantidad_restante": lot.cantidad,
        "unit_cost": unit_cost,
        "total_cost": total_cost,
    }

@router.get("/movimientos", response_model=list[InventoryMovementRead])
def list_inventory_movements(session: Session = Depends(get_session)):
    """Listar movimientos de inventario para auditoría."""
    movements = session.exec(select(InventoryMovement).order_by(InventoryMovement.created_at.desc())).all()
    result = []
    for m in movements:
        user = session.get(User, m.user_id) if getattr(m, 'user_id', None) else None
        result.append({
            "id": m.id,
            "inventory_type": m.inventory_type,
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "material_id": m.material_id,
            "material_lot_id": m.material_lot_id,
            "finished_product_id": m.finished_product_id,
            "work_order_id": m.work_order_id,
            "user_id": m.user_id,
            "user_name": user.full_name if user else None,
            "reference_code": m.reference_code,
            "notes": m.notes,
            "unit_cost": m.unit_cost,
            "total_cost": m.total_cost,
            "created_at": m.created_at,
        })
    return result


@router.get("/movimientos/reporte", response_model=InventoryMovementReportResponse)
def get_inventory_movements_report(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
    start_date: Optional[datetime] = Query(default=None, description="Filtrar desde esta fecha"),
    end_date: Optional[datetime] = Query(default=None, description="Filtrar hasta esta fecha"),
    inventory_type: Optional[str] = Query(default=None, description="material o finished_product"),
    movement_type: Optional[str] = Query(default=None, description="entrada, reserva, consumo, salida, ajuste"),
    material_id: Optional[int] = Query(default=None),
    finished_product_id: Optional[int] = Query(default=None),
    work_order_id: Optional[int] = Query(default=None),
):
    """
    Reporte filtrable de movimientos de inventario con resumen.
    Útil para auditoría operativa de materiales y producto terminado.
    """
    statement = select(InventoryMovement)

    if start_date:
        statement = statement.where(InventoryMovement.created_at >= start_date)
    if end_date:
        statement = statement.where(InventoryMovement.created_at <= end_date)
    if inventory_type:
        statement = statement.where(InventoryMovement.inventory_type == inventory_type)
    if movement_type:
        statement = statement.where(InventoryMovement.movement_type == movement_type)
    if material_id is not None:
        statement = statement.where(InventoryMovement.material_id == material_id)
    if finished_product_id is not None:
        statement = statement.where(InventoryMovement.finished_product_id == finished_product_id)
    if work_order_id is not None:
        statement = statement.where(InventoryMovement.work_order_id == work_order_id)

    statement = statement.order_by(InventoryMovement.created_at.desc())
    movements = session.exec(statement).all()

    summary = InventoryMovementReportSummary(
        total_movements=len(movements),
        total_quantity=sum(m.quantity for m in movements),
        entradas=sum(m.quantity for m in movements if m.movement_type == "entrada"),
        reservas=sum(m.quantity for m in movements if m.movement_type == "reserva"),
        consumos=sum(m.quantity for m in movements if m.movement_type == "consumo"),
        salidas=sum(m.quantity for m in movements if m.movement_type == "salida"),
        ajustes=sum(m.quantity for m in movements if m.movement_type == "ajuste"),
    )

    movements_list = []
    for m in movements:
        user = session.get(User, m.user_id) if getattr(m, 'user_id', None) else None
        movements_list.append({
            "id": m.id,
            "inventory_type": m.inventory_type,
            "movement_type": m.movement_type,
            "quantity": m.quantity,
            "material_id": m.material_id,
            "material_lot_id": m.material_lot_id,
            "finished_product_id": m.finished_product_id,
            "work_order_id": m.work_order_id,
            "user_id": m.user_id,
            "user_name": user.full_name if user else None,
            "reference_code": m.reference_code,
            "notes": m.notes,
            "unit_cost": m.unit_cost,
            "total_cost": m.total_cost,
            "created_at": m.created_at,
        })

    return InventoryMovementReportResponse(
        summary=summary,
        movements=movements_list,
    )