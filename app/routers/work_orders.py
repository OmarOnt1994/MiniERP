from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.work_order import WorkOrder, WorkOrderItem, WorkOrderStatus, WorkOrderItemLotAllocation
from app.models.material import Material, MaterialLot, InventoryMovement
from app.models.user import User
from app.models.finished_product import FinishedProduct, FinishedProductShipment
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderRead,
    WorkOrderStatusUpdate,
    WorkOrderItemRead,
    WorkOrderItemLotAllocationRead,
)
from app.schemas.finished_product import FinishedProductCreate, FinishedProductRead
from app.schemas.finished_product import FinishedProductShipmentCreate, FinishedProductShipmentRead
from app.schemas.finished_product import WorkOrderFinishedProductCreate
from app.dependencies.auth import get_current_user, require_roles
from datetime import datetime

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


def _build_work_order_item_read(session: Session, item: WorkOrderItem) -> WorkOrderItemRead:
    material = session.get(Material, item.material_id)
    allocations = session.exec(
        select(WorkOrderItemLotAllocation).where(WorkOrderItemLotAllocation.work_order_item_id == item.id)
    ).all()

    lotes_utilizados = []
    for allocation in allocations:
        lot = session.get(MaterialLot, allocation.material_lot_id)
        if lot:
            lotes_utilizados.append(
                WorkOrderItemLotAllocationRead(
                    material_lot_id=allocation.material_lot_id,
                    codigo_lote=lot.codigo_lote,
                    cantidad=allocation.cantidad,
                )
            )

    return WorkOrderItemRead(
        id=item.id,
        work_order_id=item.work_order_id,
        material_id=item.material_id,
        material_codigo=material.codigo if material else "",
        material_nombre=material.nombre if material else "",
        material_unidad=material.unidad if material else "",
        cantidad_requerida=item.cantidad_requerida,
        cantidad_asignada=item.cantidad_asignada,
        lotes_utilizados=lotes_utilizados,
    )


def _resolve_item_allocations(session: Session, item_data):
    material = session.get(Material, item_data.material_id)
    if not material:
        raise HTTPException(
            status_code=404,
            detail=f"Material con ID {item_data.material_id} no existe"
        )

    if item_data.lotes_seleccionados:
        selected_pairs = [(selection.material_lot_id, selection.cantidad) for selection in item_data.lotes_seleccionados]
        total_selected = sum(cantidad for _, cantidad in selected_pairs)
        if total_selected != item_data.cantidad_requerida:
            raise HTTPException(
                status_code=400,
                detail=f"La suma de lotes seleccionados ({total_selected}) debe coincidir con la cantidad requerida ({item_data.cantidad_requerida})"
            )

        allocations = []
        for lot_id, cantidad in selected_pairs:
            lot = session.get(MaterialLot, lot_id)
            if not lot or lot.material_id != item_data.material_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"El lote {lot_id} no pertenece al material '{material.nombre}'"
                )
            disponible = lot.cantidad - lot.cantidad_reservada
            if disponible < cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cantidad insuficiente en lote {lot.codigo_lote}. Disponible: {disponible}, Requerido: {cantidad}"
                )
            allocations.append((lot, cantidad))
        return material, allocations

    lotes = session.exec(
        select(MaterialLot)
        .where(MaterialLot.material_id == item_data.material_id)
        .where((MaterialLot.cantidad - MaterialLot.cantidad_reservada) > 0)
        .order_by(MaterialLot.fecha_entrada.asc())
    ).all()

    if not lotes:
        raise HTTPException(
            status_code=400,
            detail=f"No hay lotes disponibles para material '{material.nombre}'"
        )

    stock_total = sum(lot.cantidad - lot.cantidad_reservada for lot in lotes)
    if stock_total < item_data.cantidad_requerida:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente para material '{material.nombre}'. Disponible: {stock_total}, Requerido: {item_data.cantidad_requerida}"
        )

    allocations = []
    remaining = item_data.cantidad_requerida
    for lot in lotes:
        if remaining <= 0:
            break
        used = min(lot.cantidad, remaining)
        allocations.append((lot, used))
        remaining -= used

    return material, allocations


def _reserve_material_lots(session: Session, allocations, work_order_id: int, user_id: int):
    for lot, cantidad in allocations:
        # Lock the lot row for update to avoid concurrent reservations
        locked = session.exec(
            select(MaterialLot).where(MaterialLot.id == lot.id).with_for_update()
        ).one()
        locked.cantidad_reservada += cantidad
        session.add(locked)
        session.add(
            InventoryMovement(
                inventory_type="material",
                movement_type="reserva",
                quantity=cantidad,
                material_id=locked.material_id,
                material_lot_id=locked.id,
                work_order_id=work_order_id,
                user_id=user_id,
                reference_code=locked.codigo_lote,
                notes="Reserva para Work Order",
            )
        )


def _consume_reserved_materials(session: Session, item: WorkOrderItem, user_id: int):
    allocations = session.exec(
        select(WorkOrderItemLotAllocation).where(WorkOrderItemLotAllocation.work_order_item_id == item.id)
    ).all()
    total_item_cost = 0.0

    for allocation in allocations:
        # Lock the lot row before modifying to prevent concurrent consumption
        lot = session.exec(
            select(MaterialLot).where(MaterialLot.id == allocation.material_lot_id).with_for_update()
        ).one()
        if not lot:
            raise HTTPException(status_code=404, detail=f"Lote {allocation.material_lot_id} no encontrado")
        if lot.cantidad_reservada < allocation.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"La reserva del lote {lot.codigo_lote} es insuficiente. Reservado: {lot.cantidad_reservada}, Requerido: {allocation.cantidad}"
            )
        if lot.cantidad < allocation.cantidad:
            raise HTTPException(
                status_code=400,
                detail=f"Stock físico insuficiente en lote {lot.codigo_lote}. Disponible: {lot.cantidad}, Requerido: {allocation.cantidad}"
            )
        lot.cantidad -= allocation.cantidad
        lot.cantidad_reservada -= allocation.cantidad
        session.add(lot)

        # Determinar costo unitario: preferir costo del lote, luego costo maestro del material
        material = session.get(Material, lot.material_id)
        unit_cost = lot.costo_unitario if getattr(lot, 'costo_unitario', None) is not None else 0.0
        movement_total = unit_cost * allocation.cantidad if unit_cost else None
        if movement_total:
            total_item_cost += movement_total

        session.add(
            InventoryMovement(
                inventory_type="material",
                movement_type="consumo",
                quantity=allocation.cantidad,
                material_id=lot.material_id,
                material_lot_id=lot.id,
                work_order_id=item.work_order_id,
                user_id=user_id,
                reference_code=lot.codigo_lote,
                notes="Consumo de material para surtido de WO",
                unit_cost=unit_cost if unit_cost else None,
                total_cost=movement_total,
            )
        )

    return total_item_cost


def _get_work_order_finished_quantity(session: Session, work_order_id: int) -> float:
    finished_products = session.exec(
        select(FinishedProduct).where(FinishedProduct.work_order_id == work_order_id)
    ).all()
    return sum(product.cantidad_producida for product in finished_products)

@router.post("/", response_model=WorkOrderRead)
def create_work_order(
    wo_data: WorkOrderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("produccion", "almacen"))
):
    """
    Crear Work Order.
    Validación: Todos los materiales deben existir con lotes disponibles (FIFO).
    """
    planned_allocations = []
    for item in wo_data.items:
        material, allocations = _resolve_item_allocations(session, item)
        planned_allocations.append((item, material, allocations))

    db_wo = WorkOrder(
        numero_orden=wo_data.numero_orden,
        descripcion=wo_data.descripcion,
        cantidad_a_producir=wo_data.cantidad_a_producir,
        notas=wo_data.notas,
        status=WorkOrderStatus.pendiente,
    )
    session.add(db_wo)
    session.flush()

    for item_data, _, allocations in planned_allocations:
        wo_item = WorkOrderItem(
            work_order_id=db_wo.id,
            material_id=item_data.material_id,
            cantidad_requerida=item_data.cantidad_requerida,
            cantidad_asignada=0.0,
        )
        session.add(wo_item)
        session.flush()

        for lot, cantidad in allocations:
            session.add(
                WorkOrderItemLotAllocation(
                    work_order_item_id=wo_item.id,
                    material_lot_id=lot.id,
                    cantidad=cantidad,
                )
            )

        _reserve_material_lots(session, allocations, db_wo.id, current_user.id)

    session.add(
        InventoryMovement(
            inventory_type="material",
            movement_type="reserva",
            quantity=wo_data.cantidad_a_producir,
            work_order_id=db_wo.id,
            user_id=current_user.id,
            reference_code=wo_data.numero_orden,
            notes="Reserva de materiales para WO",
        )
    )

    session.commit()
    session.refresh(db_wo)
    
    # Cargar items para la respuesta
    items = session.exec(
        select(WorkOrderItem).where(WorkOrderItem.work_order_id == db_wo.id)
    ).all()
    
    return WorkOrderRead(
        id=db_wo.id,
        numero_orden=db_wo.numero_orden,
        descripcion=db_wo.descripcion,
        status=db_wo.status.value,
        cantidad_a_producir=db_wo.cantidad_a_producir,
        notas=db_wo.notas,
        items=[_build_work_order_item_read(session, item) for item in items],
        created_at=db_wo.created_at,
        updated_at=db_wo.updated_at
    )

@router.get("/", response_model=list[WorkOrderRead])
def list_work_orders(session: Session = Depends(get_session)):
    """Listar todas las Work Orders"""
    wos = session.exec(select(WorkOrder)).all()
    result = []
    for wo in wos:
        items = session.exec(
            select(WorkOrderItem).where(WorkOrderItem.work_order_id == wo.id)
        ).all()
        result.append(WorkOrderRead(
            id=wo.id,
            numero_orden=wo.numero_orden,
            descripcion=wo.descripcion,
            status=wo.status.value,
            cantidad_a_producir=wo.cantidad_a_producir,
            notas=wo.notas,
            items=[_build_work_order_item_read(session, item) for item in items],
            created_at=wo.created_at,
            updated_at=wo.updated_at
        ))
    return result

@router.get("/{wo_id}", response_model=WorkOrderRead)
def get_work_order(wo_id: int, session: Session = Depends(get_session)):
    """Obtener detalle de una Work Order"""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order no encontrada")
    
    items = session.exec(
        select(WorkOrderItem).where(WorkOrderItem.work_order_id == wo.id)
    ).all()
    
    return WorkOrderRead(
        id=wo.id,
        numero_orden=wo.numero_orden,
        descripcion=wo.descripcion,
        status=wo.status.value,
        cantidad_a_producir=wo.cantidad_a_producir,
        notas=wo.notas,
        items=[_build_work_order_item_read(session, item) for item in items],
        created_at=wo.created_at,
        updated_at=wo.updated_at
    )

@router.put("/{wo_id}/status", response_model=WorkOrderRead)
def update_work_order_status(
    wo_id: int,
    status_update: WorkOrderStatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("produccion", "almacen"))
):
    """
    Cambiar status de Work Order.
    - pendiente: estado inicial
    - surtido: materiales restados del stock usando FIFO
    - en_proceso: en producción
    - finalizado: crea entrada en inventario de producto terminado
    """
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order no encontrada")

    valid_statuses = [s.value for s in WorkOrderStatus]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status inválido. Permitidos: {', '.join(valid_statuses)}"
        )

    if status_update.status == "surtido":
        items = session.exec(
            select(WorkOrderItem).where(WorkOrderItem.work_order_id == wo.id)
        ).all()

        for item in items:
            material = session.get(Material, item.material_id)
            if not material:
                raise HTTPException(status_code=404, detail=f"Material {item.material_id} no encontrado")

            _consume_reserved_materials(session, item, current_user.id)

            item.cantidad_asignada = item.cantidad_requerida
            session.add(item)

    if status_update.status == "finalizado":
        finished_quantity = _get_work_order_finished_quantity(session, wo.id)
        if finished_quantity > 0 and finished_quantity < wo.cantidad_a_producir:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No se puede cerrar la WO porque solo hay {finished_quantity} "
                    f"de {wo.cantidad_a_producir} unidades terminadas"
                ),
            )

        existing_finished = session.exec(
            select(FinishedProduct).where(FinishedProduct.work_order_id == wo.id)
        ).first()
        if not existing_finished:
            finished_product = FinishedProduct(
                codigo=f"FP-{wo.numero_orden}",
                lote_produccion=wo.numero_orden,
                nombre=wo.descripcion,
                descripcion=wo.notas,
                cantidad_producida=wo.cantidad_a_producir,
                cantidad_disponible=wo.cantidad_a_producir,
                costo_total=None,
                work_order_id=wo.id,
            )
            session.add(finished_product)
            session.flush()
            session.add(
                InventoryMovement(
                    inventory_type="finished_product",
                    movement_type="entrada",
                    quantity=wo.cantidad_a_producir,
                    finished_product_id=finished_product.id,
                    work_order_id=wo.id,
                    user_id=current_user.id,
                    reference_code=finished_product.codigo,
                    notes="Entrada automática por finalización de WO",
                )
            )
            # Calcular costo total consumido por la WO (sumatoria de movimientos de consumo)
            consumo_movs = session.exec(
                select(InventoryMovement)
                .where(InventoryMovement.work_order_id == wo.id)
                .where(InventoryMovement.movement_type == "consumo")
            ).all()
            total_consumo_cost = sum(m.total_cost or 0.0 for m in consumo_movs)
            finished_product.costo_total = total_consumo_cost if total_consumo_cost > 0 else None
            session.add(finished_product)

    wo.status = WorkOrderStatus(status_update.status)
    wo.updated_at = datetime.utcnow()
    session.add(wo)
    session.commit()
    session.refresh(wo)

    items = session.exec(
        select(WorkOrderItem).where(WorkOrderItem.work_order_id == wo.id)
    ).all()

    return WorkOrderRead(
        id=wo.id,
        numero_orden=wo.numero_orden,
        descripcion=wo.descripcion,
        status=wo.status.value,
        cantidad_a_producir=wo.cantidad_a_producir,
        notas=wo.notas,
        items=[_build_work_order_item_read(session, item) for item in items],
        created_at=wo.created_at,
        updated_at=wo.updated_at,
    )

# Router para Finished Products
finished_router = APIRouter(prefix="/finished-products", tags=["finished-products"])

@finished_router.post("/", response_model=FinishedProductRead)
def create_finished_product(
    fp_data: FinishedProductCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("produccion", "almacen"))
):
    """
    Registrar producto terminado.
    Asociado a una Work Order finalizada.
    """
    # Validar que la WO exista y esté finalizada
    wo = session.get(WorkOrder, fp_data.work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order no encontrada")
    
    # Verificar codigo único de producto terminado
    exists_fp = session.exec(select(FinishedProduct).where(FinishedProduct.codigo == fp_data.codigo)).first()
    if exists_fp:
        raise HTTPException(status_code=400, detail=f"Ya existe un producto terminado con codigo '{fp_data.codigo}'")

    db_fp = FinishedProduct(
        codigo=fp_data.codigo,
        lote_produccion=fp_data.lote_produccion or f"WO-{fp_data.work_order_id}",
        nombre=fp_data.nombre,
        descripcion=fp_data.descripcion,
        cantidad_producida=fp_data.cantidad_producida,
        cantidad_disponible=fp_data.cantidad_disponible if fp_data.cantidad_disponible is not None else fp_data.cantidad_producida,
        costo_total=fp_data.costo_total,
        work_order_id=fp_data.work_order_id
    )
    session.add(db_fp)
    session.flush()
    session.add(
        InventoryMovement(
            inventory_type="finished_product",
            movement_type="entrada",
            quantity=db_fp.cantidad_disponible,
            finished_product_id=db_fp.id,
            work_order_id=db_fp.work_order_id,
            user_id=current_user.id,
            reference_code=db_fp.codigo,
            notes="Entrada manual de producto terminado",
        )
    )
    session.commit()
    session.refresh(db_fp)
    return db_fp


@router.post("/{wo_id}/finished-products", response_model=FinishedProductRead)
def create_work_order_finished_product(
    wo_id: int,
    fp_data: WorkOrderFinishedProductCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("produccion", "almacen"))
):
    """Registrar un lote parcial de producto terminado asociado a una Work Order."""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order no encontrada")

    exists_fp = session.exec(select(FinishedProduct).where(FinishedProduct.codigo == fp_data.codigo)).first()
    if exists_fp:
        raise HTTPException(status_code=400, detail=f"Ya existe un producto terminado con codigo '{fp_data.codigo}'")

    db_fp = FinishedProduct(
        codigo=fp_data.codigo,
        lote_produccion=fp_data.lote_produccion or f"WO-{wo.id}",
        nombre=fp_data.nombre or wo.descripcion,
        descripcion=fp_data.descripcion or wo.notas,
        cantidad_producida=fp_data.cantidad_producida,
        cantidad_disponible=fp_data.cantidad_disponible if fp_data.cantidad_disponible is not None else fp_data.cantidad_producida,
        costo_total=fp_data.costo_total,
        work_order_id=wo.id,
    )
    session.add(db_fp)
    session.flush()
    session.add(
        InventoryMovement(
            inventory_type="finished_product",
            movement_type="entrada",
            quantity=db_fp.cantidad_disponible,
            finished_product_id=db_fp.id,
            work_order_id=db_fp.work_order_id,
            user_id=current_user.id,
            reference_code=db_fp.codigo,
            notes="Entrada parcial de producto terminado",
        )
    )
    session.commit()
    session.refresh(db_fp)
    return db_fp


@router.get("/{wo_id}/production-summary")
def get_work_order_production_summary(
    wo_id: int,
    session: Session = Depends(get_session),
):
    """Resumen de producción terminada vs. planificada para una Work Order."""
    wo = session.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order no encontrada")

    finished_products = session.exec(
        select(FinishedProduct).where(FinishedProduct.work_order_id == wo.id)
    ).all()
    total_producido = sum(product.cantidad_producida for product in finished_products)
    total_disponible = sum(product.cantidad_disponible for product in finished_products)

    return {
        "work_order_id": wo.id,
        "cantidad_a_producir": wo.cantidad_a_producir,
        "cantidad_producida": total_producido,
        "cantidad_disponible": total_disponible,
        "cantidad_pendiente": max(wo.cantidad_a_producir - total_producido, 0.0),
        "esta_completa": total_producido >= wo.cantidad_a_producir,
    }

@finished_router.get("/", response_model=list[FinishedProductRead])
def list_finished_products(session: Session = Depends(get_session)):
    """Listar productos terminados"""
    return session.exec(select(FinishedProduct)).all()


@finished_router.post("/shipments", response_model=FinishedProductShipmentRead)
def create_finished_product_shipment(
    shipment_data: FinishedProductShipmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("despachos", "almacen"))
):
    """Registrar salida/envío de producto terminado y descontar inventario."""
    finished_product = session.get(FinishedProduct, shipment_data.finished_product_id)
    if not finished_product:
        raise HTTPException(status_code=404, detail="Producto terminado no encontrado")

    if finished_product.cantidad_disponible < shipment_data.cantidad:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {finished_product.cantidad_disponible}, Solicitado: {shipment_data.cantidad}"
        )

    finished_product.cantidad_disponible -= shipment_data.cantidad
    session.add(finished_product)

    shipment = FinishedProductShipment(
        finished_product_id=shipment_data.finished_product_id,
        cantidad=shipment_data.cantidad,
        destinatario=shipment_data.destinatario,
        documento_envio=shipment_data.documento_envio,
        observaciones=shipment_data.observaciones,
    )
    session.add(shipment)
    session.flush()
    session.add(
        InventoryMovement(
            inventory_type="finished_product",
            movement_type="salida",
            quantity=shipment_data.cantidad,
            finished_product_id=finished_product.id,
            user_id=current_user.id,
            reference_code=finished_product.codigo,
            notes=shipment_data.observaciones or "Salida por envío",
        )
    )
    session.commit()
    session.refresh(shipment)
    return shipment

@finished_router.get("/shipments", response_model=list[FinishedProductShipmentRead])
def list_finished_product_shipments(session: Session = Depends(get_session)):
    """Listar envíos de producto terminado."""
    return session.exec(select(FinishedProductShipment)).all()


@finished_router.get("/{product_id}", response_model=FinishedProductRead)
def get_finished_product(product_id: int, session: Session = Depends(get_session)):
    """Obtener detalle de producto terminado"""
    fp = session.get(FinishedProduct, product_id)
    if not fp:
        raise HTTPException(status_code=404, detail="Producto terminado no encontrado")
    return fp
