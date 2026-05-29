from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class WorkOrderItemLotInput(BaseModel):
    material_lot_id: int
    cantidad: float = Field(gt=0, description="Cantidad tomada del lote")

class WorkOrderItemCreate(BaseModel):
    material_id: int
    cantidad_requerida: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    lotes_seleccionados: List[WorkOrderItemLotInput] = Field(default_factory=list)

class WorkOrderItemLotAllocationRead(BaseModel):
    material_lot_id: int
    codigo_lote: str
    cantidad: float

class WorkOrderCreate(BaseModel):
    numero_orden: str
    descripcion: str
    cantidad_a_producir: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    items: List[WorkOrderItemCreate]
    notas: Optional[str] = None

class WorkOrderItemRead(BaseModel):
    id: int
    work_order_id: int
    material_id: int
    material_codigo: str
    material_nombre: str
    material_unidad: str
    cantidad_requerida: float
    cantidad_asignada: float
    lotes_utilizados: List[WorkOrderItemLotAllocationRead] = Field(default_factory=list)

class WorkOrderRead(BaseModel):
    id: int
    numero_orden: str
    descripcion: str
    status: str
    cantidad_a_producir: float
    notas: Optional[str]
    items: List[WorkOrderItemRead]
    created_at: datetime
    updated_at: datetime

class WorkOrderStatusUpdate(BaseModel):
    status: str = Field(description="Estado: pendiente, surtido, en_proceso, finalizado")

class FinishedProductCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    cantidad_producida: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    costo_total: Optional[float] = None
    work_order_id: int

class FinishedProductRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    cantidad_producida: float
    costo_total: Optional[float]
    work_order_id: int
    created_at: datetime
