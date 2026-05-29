from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class WorkOrderStatus(str, Enum):
    pendiente = "pendiente"
    surtido = "surtido"
    en_proceso = "en_proceso"
    finalizado = "finalizado"

class WorkOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    numero_orden: str = Field(unique=True, index=True)
    descripcion: str
    status: WorkOrderStatus = Field(default=WorkOrderStatus.pendiente)
    cantidad_a_producir: float
    notas: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WorkOrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_id: int = Field(foreign_key="workorder.id")
    material_id: int = Field(foreign_key="material.id")
    cantidad_requerida: float
    cantidad_asignada: float = 0.0  # Se completa cuando se marca como "surtido"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WorkOrderItemLotAllocation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    work_order_item_id: int = Field(foreign_key="workorderitem.id")
    material_lot_id: int = Field(foreign_key="materiallot.id")
    cantidad: float = Field(gt=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
