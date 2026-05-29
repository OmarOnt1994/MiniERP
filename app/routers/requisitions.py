from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.dependencies.auth import require_roles
from app.models.material import Material, MaterialLot, InventoryMovement
from app.models.requisition import (
    MaterialRequisition,
    MaterialRequisitionItem,
    MaterialRequisitionStatus,
)
from app.models.user import User
from app.schemas.requisition import (
    MaterialRequisitionCreate,
    MaterialRequisitionItemRead,
    MaterialRequisitionRead,
)

router = APIRouter(prefix="/requisitions", tags=["requisitions"])


def _next_requisition_code(session: Session) -> str:
    count = session.exec(select(MaterialRequisition)).all()
    return f"REQ-{len(count) + 1:06d}"


def _build_requisition_read(session: Session, req: MaterialRequisition) -> MaterialRequisitionRead:
    items = session.exec(
        select(MaterialRequisitionItem).where(MaterialRequisitionItem.requisition_id == req.id)
    ).all()
    return MaterialRequisitionRead(
        id=req.id,
        codigo=req.codigo,
        work_order_id=req.work_order_id,
        requester_area=req.requester_area,
        purpose=req.purpose,
        is_secondary=req.is_secondary,
        status=req.status.value,
        requested_by_user_id=req.requested_by_user_id,
        approved_by_user_id=req.approved_by_user_id,
        delivered_by_user_id=req.delivered_by_user_id,
        notes=req.notes,
        created_at=req.created_at,
        approved_at=req.approved_at,
        delivered_at=req.delivered_at,
        items=[MaterialRequisitionItemRead.model_validate(item) for item in items],
    )


@router.post("/", response_model=MaterialRequisitionRead)
def create_requisition(
    payload: MaterialRequisitionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="La requisicion requiere al menos un item")

    code = _next_requisition_code(session)
    requisition = MaterialRequisition(
        codigo=code,
        work_order_id=payload.work_order_id,
        requester_area=payload.requester_area,
        purpose=payload.purpose,
        is_secondary=payload.is_secondary,
        status=MaterialRequisitionStatus.pendiente,
        requested_by_user_id=current_user.id,
        notes=payload.notes,
    )
    session.add(requisition)
    session.flush()

    for item in payload.items:
        material = session.get(Material, item.material_id)
        if not material:
            raise HTTPException(status_code=404, detail=f"Material {item.material_id} no encontrado")
        session.add(
            MaterialRequisitionItem(
                requisition_id=requisition.id,
                material_id=item.material_id,
                quantity=item.quantity,
                notes=item.notes,
            )
        )

    session.commit()
    session.refresh(requisition)
    return _build_requisition_read(session, requisition)


@router.get("/", response_model=list[MaterialRequisitionRead])
def list_requisitions(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    requisitions = session.exec(select(MaterialRequisition).order_by(MaterialRequisition.created_at.desc())).all()
    return [_build_requisition_read(session, req) for req in requisitions]


@router.get("/{requisition_id}", response_model=MaterialRequisitionRead)
def get_requisition(
    requisition_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    req = session.get(MaterialRequisition, requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisicion no encontrada")
    return _build_requisition_read(session, req)


@router.put("/{requisition_id}/approve", response_model=MaterialRequisitionRead)
def approve_requisition(
    requisition_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen")),
):
    req = session.get(MaterialRequisition, requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisicion no encontrada")
    if req.status in (MaterialRequisitionStatus.entregada, MaterialRequisitionStatus.cancelada):
        raise HTTPException(status_code=400, detail="No se puede aprobar una requisicion cerrada")

    req.status = MaterialRequisitionStatus.aprobada
    req.approved_by_user_id = current_user.id
    req.approved_at = datetime.utcnow()
    session.add(req)
    session.commit()
    session.refresh(req)
    return _build_requisition_read(session, req)


@router.put("/{requisition_id}/deliver", response_model=MaterialRequisitionRead)
def deliver_requisition(
    requisition_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "despachos")),
):
    req = session.get(MaterialRequisition, requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisicion no encontrada")
    if req.status == MaterialRequisitionStatus.entregada:
        raise HTTPException(status_code=400, detail="La requisicion ya fue entregada")
    if req.status == MaterialRequisitionStatus.cancelada:
        raise HTTPException(status_code=400, detail="La requisicion esta cancelada")

    items = session.exec(
        select(MaterialRequisitionItem).where(MaterialRequisitionItem.requisition_id == req.id)
    ).all()

    # First validate stock availability for all items.
    for item in items:
        lots = session.exec(
            select(MaterialLot)
            .where(MaterialLot.material_id == item.material_id)
            .where((MaterialLot.cantidad - MaterialLot.cantidad_reservada) > 0)
            .order_by(MaterialLot.fecha_entrada.asc())
        ).all()
        available = sum(max(0.0, lot.cantidad - lot.cantidad_reservada) for lot in lots)
        if available < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para material {item.material_id}. Disponible: {available}, requerido: {item.quantity}",
            )

    # Consume FIFO from lots and register inventory movement.
    for item in items:
        pending = item.quantity
        lots = session.exec(
            select(MaterialLot)
            .where(MaterialLot.material_id == item.material_id)
            .where((MaterialLot.cantidad - MaterialLot.cantidad_reservada) > 0)
            .order_by(MaterialLot.fecha_entrada.asc())
        ).all()

        for lot in lots:
            if pending <= 0:
                break

            locked_lot = session.exec(
                select(MaterialLot).where(MaterialLot.id == lot.id).with_for_update()
            ).one()
            available = max(0.0, locked_lot.cantidad - locked_lot.cantidad_reservada)
            if available <= 0:
                continue

            used = min(available, pending)
            locked_lot.cantidad -= used
            session.add(locked_lot)

            unit_cost = locked_lot.costo_unitario
            total_cost = (unit_cost * used) if unit_cost is not None else None

            session.add(
                InventoryMovement(
                    inventory_type="material",
                    movement_type="salida",
                    quantity=used,
                    material_id=item.material_id,
                    material_lot_id=locked_lot.id,
                    work_order_id=req.work_order_id,
                    user_id=current_user.id,
                    reference_code=req.codigo,
                    notes=f"Salida por requisicion ({req.purpose or 'material secundario'})",
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                )
            )
            pending -= used

        item.delivered_quantity = item.quantity
        session.add(item)

    req.status = MaterialRequisitionStatus.entregada
    req.delivered_by_user_id = current_user.id
    req.delivered_at = datetime.utcnow()
    session.add(req)
    session.commit()
    session.refresh(req)
    return _build_requisition_read(session, req)


@router.put("/{requisition_id}/cancel", response_model=MaterialRequisitionRead)
def cancel_requisition(
    requisition_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion")),
):
    req = session.get(MaterialRequisition, requisition_id)
    if not req:
        raise HTTPException(status_code=404, detail="Requisicion no encontrada")
    if req.status == MaterialRequisitionStatus.entregada:
        raise HTTPException(status_code=400, detail="No se puede cancelar una requisicion entregada")

    req.status = MaterialRequisitionStatus.cancelada
    session.add(req)
    session.commit()
    session.refresh(req)
    return _build_requisition_read(session, req)
