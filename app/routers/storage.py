from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.dependencies.auth import require_roles
from app.models.material import MaterialLot, InventoryMovement
from app.models.storage import Almacen, Locacion
from app.models.transfer import MaterialTransfer, MaterialTransferBatch
from app.models.user import User
from app.schemas.storage import (
    AlmacenCreate,
    AlmacenRead,
    LocacionCreate,
    LocacionRead,
    MaterialTransferBatchCreate,
    MaterialTransferBatchRead,
    MaterialTransferCreate,
    MaterialTransferRead,
)

router = APIRouter(prefix="/storage", tags=["storage"])


@router.post("/almacenes", response_model=AlmacenRead)
def create_almacen(
    payload: AlmacenCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen")),
):
    exists = session.exec(select(Almacen).where(Almacen.codigo == payload.codigo)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe un almacen con ese codigo")

    almacen = Almacen(**payload.model_dump())
    session.add(almacen)
    session.commit()
    session.refresh(almacen)
    return almacen


@router.get("/almacenes", response_model=list[AlmacenRead])
def list_almacenes(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    return session.exec(select(Almacen).order_by(Almacen.codigo.asc())).all()


@router.post("/locaciones", response_model=LocacionRead)
def create_locacion(
    payload: LocacionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen")),
):
    almacen = session.get(Almacen, payload.almacen_id)
    if not almacen:
        raise HTTPException(status_code=404, detail="Almacen no encontrado")

    exists = session.exec(
        select(Locacion)
        .where(Locacion.almacen_id == payload.almacen_id)
        .where(Locacion.codigo == payload.codigo)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Ya existe una locacion con ese codigo en el almacen")

    locacion = Locacion(**payload.model_dump())
    session.add(locacion)
    session.commit()
    session.refresh(locacion)
    return locacion


@router.get("/locaciones", response_model=list[LocacionRead])
def list_locaciones(
    almacen_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    stmt = select(Locacion)
    if almacen_id is not None:
        stmt = stmt.where(Locacion.almacen_id == almacen_id)
    return session.exec(stmt.order_by(Locacion.codigo.asc())).all()


def _execute_transfer_line(
    payload: MaterialTransferCreate,
    session: Session,
    current_user: User,
    batch_id: int | None,
) -> MaterialTransfer:
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="La cantidad a transferir debe ser positiva")

    source_lot = session.exec(
        select(MaterialLot).where(MaterialLot.id == payload.source_lot_id).with_for_update()
    ).first()
    if not source_lot:
        raise HTTPException(status_code=404, detail="Lote origen no encontrado")

    source_available = source_lot.cantidad - source_lot.cantidad_reservada
    if source_available < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente en lote origen. Disponible: {source_available}, requerido: {payload.quantity}",
        )

    destination_almacen_id = payload.destination_almacen_id
    destination_locacion_id = payload.destination_locacion_id

    if destination_locacion_id is not None:
        destination_loc = session.get(Locacion, destination_locacion_id)
        if not destination_loc:
            raise HTTPException(status_code=404, detail="Locacion destino no encontrada")
        if destination_almacen_id is not None and destination_loc.almacen_id != destination_almacen_id:
            raise HTTPException(status_code=400, detail="La locacion destino no pertenece al almacen destino")
        destination_almacen_id = destination_loc.almacen_id

    if destination_almacen_id is not None:
        almacen = session.get(Almacen, destination_almacen_id)
        if not almacen:
            raise HTTPException(status_code=404, detail="Almacen destino no encontrado")

    if destination_almacen_id is None and destination_locacion_id is None:
        raise HTTPException(status_code=400, detail="Debes indicar almacen o locacion de destino")

    if (
        destination_almacen_id == source_lot.almacen_id
        and destination_locacion_id == source_lot.locacion_id
    ):
        raise HTTPException(status_code=400, detail="El destino no puede ser igual al origen")

    # Create transfer record first to generate the transfer code from database
    transfer = MaterialTransfer(
        batch_id=batch_id,
        material_id=source_lot.material_id,
        source_lot_id=source_lot.id,
        destination_lot_id=0,  # Temporary, will be updated after destination_lot is created
        source_almacen_id=source_lot.almacen_id,
        source_locacion_id=source_lot.locacion_id,
        destination_almacen_id=destination_almacen_id,
        destination_locacion_id=destination_locacion_id,
        quantity=payload.quantity,
        user_id=current_user.id,
        notes=payload.notes,
    )
    session.add(transfer)
    session.flush()  # Generate the codigo from the database sequence

    transfer_code = transfer.codigo
    source_lot.cantidad -= payload.quantity
    session.add(source_lot)

    destination_code = payload.destination_lot_code or f"{source_lot.codigo_lote}-TR-{int(datetime.utcnow().timestamp())}"
    existing_dest_lot = session.exec(
        select(MaterialLot)
        .where(MaterialLot.material_id == source_lot.material_id)
        .where(MaterialLot.codigo_lote == destination_code)
    ).first()

    if existing_dest_lot:
        destination_lot = existing_dest_lot
        if destination_lot.almacen_id != destination_almacen_id or destination_lot.locacion_id != destination_locacion_id:
            raise HTTPException(
                status_code=400,
                detail="El codigo de lote destino ya existe en otra ubicacion",
            )
        destination_lot.cantidad += payload.quantity
    else:
        destination_lot = MaterialLot(
            material_id=source_lot.material_id,
            codigo_lote=destination_code,
            cantidad=payload.quantity,
            cantidad_reservada=0.0,
            almacen_id=destination_almacen_id,
            locacion_id=destination_locacion_id,
            costo_unitario=source_lot.costo_unitario,
            costo_total=(source_lot.costo_unitario * payload.quantity) if source_lot.costo_unitario is not None else None,
            fecha_caducidad=source_lot.fecha_caducidad,
            notas=f"Lote generado por transferencia {transfer_code}",
        )
        session.add(destination_lot)

    session.flush()

    # Update transfer with the correct destination_lot_id
    transfer.destination_lot_id = destination_lot.id
    session.add(transfer)

    session.add(
        InventoryMovement(
            inventory_type="material",
            movement_type="traslado_salida",
            quantity=payload.quantity,
            material_id=source_lot.material_id,
            material_lot_id=source_lot.id,
            user_id=current_user.id,
            reference_code=transfer_code,
            notes=f"Salida por transferencia a lote {destination_lot.codigo_lote}",
            unit_cost=source_lot.costo_unitario,
            total_cost=(source_lot.costo_unitario * payload.quantity) if source_lot.costo_unitario is not None else None,
        )
    )
    session.add(
        InventoryMovement(
            inventory_type="material",
            movement_type="traslado_entrada",
            quantity=payload.quantity,
            material_id=destination_lot.material_id,
            material_lot_id=destination_lot.id,
            user_id=current_user.id,
            reference_code=transfer_code,
            notes=f"Entrada por transferencia desde lote {source_lot.codigo_lote}",
            unit_cost=destination_lot.costo_unitario,
            total_cost=(destination_lot.costo_unitario * payload.quantity) if destination_lot.costo_unitario is not None else None,
        )
    )

    return transfer


@router.post("/transfers", response_model=MaterialTransferRead)
def create_transfer(
    payload: MaterialTransferCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen")),
):
    transfer = _execute_transfer_line(payload=payload, session=session, current_user=current_user, batch_id=None)
    session.add(transfer)
    session.commit()
    session.refresh(transfer)
    return transfer


@router.post("/transfers/batch", response_model=MaterialTransferBatchRead)
def create_transfer_batch(
    payload: MaterialTransferBatchCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen")),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un movimiento")

    batch = MaterialTransferBatch(
        created_by_user_id=current_user.id,
        notes=payload.notes,
        item_count=len(payload.items),
    )
    session.add(batch)
    session.flush()  # Generate the folio from the database sequence

    created_lines: list[MaterialTransfer] = []
    for item in payload.items:
        line = _execute_transfer_line(payload=item, session=session, current_user=current_user, batch_id=batch.id)
        created_lines.append(line)

    session.commit()
    session.refresh(batch)
    for line in created_lines:
        session.refresh(line)

    return MaterialTransferBatchRead(
        id=batch.id,
        folio=batch.folio,
        created_by_user_id=batch.created_by_user_id,
        notes=batch.notes,
        item_count=batch.item_count,
        created_at=batch.created_at,
        items=[MaterialTransferRead.model_validate(line) for line in created_lines],
    )


@router.get("/transfers", response_model=list[MaterialTransferRead])
def list_transfers(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    return session.exec(select(MaterialTransfer).order_by(MaterialTransfer.created_at.desc())).all()


@router.get("/transfers/batches", response_model=list[MaterialTransferBatchRead])
def list_transfer_batches(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("almacen", "produccion", "despachos")),
):
    batches = session.exec(select(MaterialTransferBatch).order_by(MaterialTransferBatch.created_at.desc())).all()
    result: list[MaterialTransferBatchRead] = []
    for batch in batches:
        lines = session.exec(
            select(MaterialTransfer)
            .where(MaterialTransfer.batch_id == batch.id)
            .order_by(MaterialTransfer.created_at.asc())
        ).all()
        result.append(
            MaterialTransferBatchRead(
                id=batch.id,
                folio=batch.folio,
                created_by_user_id=batch.created_by_user_id,
                notes=batch.notes,
                item_count=batch.item_count,
                created_at=batch.created_at,
                items=[MaterialTransferRead.model_validate(line) for line in lines],
            )
        )
    return result
