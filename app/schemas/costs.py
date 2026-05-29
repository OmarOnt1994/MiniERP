from pydantic import BaseModel
from typing import Optional, List


class WorkOrderMaterialBreakdown(BaseModel):
    material_id: int
    material_codigo: Optional[str]
    material_nombre: Optional[str]
    quantity: float
    total_cost: Optional[float]
    avg_unit_cost: Optional[float]


class WorkOrderCostsResponse(BaseModel):
    work_order_id: int
    total_cost: Optional[float]
    cost_per_finished_unit: Optional[float]
    by_material: List[WorkOrderMaterialBreakdown]


class MaterialLotBreakdown(BaseModel):
    material_lot_id: int
    codigo_lote: Optional[str]
    quantity: float
    total_cost: Optional[float]
    avg_unit_cost: Optional[float]


class MaterialCostsResponse(BaseModel):
    material_id: int
    period_total_cost: Optional[float]
    period_avg_unit_cost: Optional[float]
    by_lot: List[MaterialLotBreakdown]
