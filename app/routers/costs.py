from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import Optional
from datetime import datetime

from app.core.database import get_session
from app.models.material import InventoryMovement, Material, MaterialLot
from app.schemas.costs import WorkOrderCostsResponse, WorkOrderMaterialBreakdown, MaterialCostsResponse, MaterialLotBreakdown
from app.dependencies.auth import require_roles

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/work-orders/{wo_id}", response_model=WorkOrderCostsResponse)
def get_work_order_costs(
    wo_id: int,
    session: Session = Depends(get_session),
    current_user = Depends(require_roles("almacen", "produccion", "contabilidad")),
):
    # Total cost for consumptions linked to the WO
    total_stmt = select(func.sum(InventoryMovement.total_cost)).where(
        InventoryMovement.movement_type == "consumo",
        InventoryMovement.work_order_id == wo_id,
    )
    total_result = session.exec(total_stmt).one()
    try:
        total_cost = total_result[0] or 0.0
    except Exception:
        total_cost = total_result or 0.0

    # Breakdown by material
    stmt = (
        select(
            InventoryMovement.material_id,
            func.sum(InventoryMovement.quantity).label("quantity"),
            func.sum(InventoryMovement.total_cost).label("total_cost"),
            func.avg(InventoryMovement.unit_cost).label("avg_unit_cost"),
        )
        .where(InventoryMovement.movement_type == "consumo")
        .where(InventoryMovement.work_order_id == wo_id)
        .group_by(InventoryMovement.material_id)
    )

    rows = session.exec(stmt).all()
    by_material = []
    for row in rows:
        material = session.get(Material, row[0]) if row[0] is not None else None
        by_material.append(
            WorkOrderMaterialBreakdown(
                material_id=row[0] if row[0] is not None else 0,
                material_codigo=material.codigo if material else None,
                material_nombre=material.nombre if material else None,
                quantity=row[1] or 0.0,
                total_cost=row[2],
                avg_unit_cost=row[3],
            )
        )

    # Try to compute cost per finished unit: fetch produced finished product quantity if exists
    # We can try to derive from finished products table via InventoryMovement finished_product_id or work orders
    # For now, return None to let frontend compute if needed
    cost_per_finished_unit = None

    return WorkOrderCostsResponse(
        work_order_id=wo_id,
        total_cost=total_cost,
        cost_per_finished_unit=cost_per_finished_unit,
        by_material=by_material,
    )


@router.get("/materials/{material_id}", response_model=MaterialCostsResponse)
def get_material_costs(
    material_id: int,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    session: Session = Depends(get_session),
    current_user = Depends(require_roles("almacen", "contabilidad")),
):
    # Base filters: movement_type consumo and material_id
    base = select(InventoryMovement).where(
        InventoryMovement.movement_type == "consumo",
        InventoryMovement.material_id == material_id,
    )
    if start_date:
        base = base.where(InventoryMovement.created_at >= start_date)
    if end_date:
        base = base.where(InventoryMovement.created_at <= end_date)

    # Period totals
    total_stmt = select(func.sum(InventoryMovement.total_cost), func.avg(InventoryMovement.unit_cost)).where(
        InventoryMovement.movement_type == "consumo",
        InventoryMovement.material_id == material_id,
    )
    if start_date:
        total_stmt = total_stmt.where(InventoryMovement.created_at >= start_date)
    if end_date:
        total_stmt = total_stmt.where(InventoryMovement.created_at <= end_date)

    total_row = session.exec(total_stmt).one()
    try:
        period_total_cost = total_row[0] or 0.0
        period_avg_unit_cost = total_row[1] if total_row[1] is not None else None
    except Exception:
        period_total_cost = total_row or 0.0
        period_avg_unit_cost = None

    # Breakdown by lot
    lot_stmt = (
        select(
            InventoryMovement.material_lot_id,
            func.sum(InventoryMovement.quantity).label("quantity"),
            func.sum(InventoryMovement.total_cost).label("total_cost"),
            func.avg(InventoryMovement.unit_cost).label("avg_unit_cost"),
        )
        .where(InventoryMovement.movement_type == "consumo")
        .where(InventoryMovement.material_id == material_id)
        .group_by(InventoryMovement.material_lot_id)
    )
    if start_date:
        lot_stmt = lot_stmt.where(InventoryMovement.created_at >= start_date)
    if end_date:
        lot_stmt = lot_stmt.where(InventoryMovement.created_at <= end_date)

    rows = session.exec(lot_stmt).all()
    by_lot = []
    for row in rows:
        lot = session.get(MaterialLot, row[0]) if row[0] is not None else None
        by_lot.append(
            MaterialLotBreakdown(
                material_lot_id=row[0] if row[0] is not None else 0,
                codigo_lote=lot.codigo_lote if lot else None,
                quantity=row[1] or 0.0,
                total_cost=row[2],
                avg_unit_cost=row[3],
            )
        )

    return MaterialCostsResponse(
        material_id=material_id,
        period_total_cost=period_total_cost,
        period_avg_unit_cost=period_avg_unit_cost,
        by_lot=by_lot,
    )
