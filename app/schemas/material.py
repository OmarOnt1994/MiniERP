from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MaterialCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    unidad: str = "pieza"

class MaterialRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    unidad: str
    created_at: datetime

class MaterialUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

class MaterialLotCreate(BaseModel):
    """Entrada de material con lote"""
    codigo_lote: str
    cantidad: float = Field(gt=0)
    almacen_id: Optional[int] = None
    locacion_id: Optional[int] = None
    costo_unitario: Optional[float] = None
    fecha_caducidad: Optional[datetime] = None
    notas: Optional[str] = None

class MaterialLotRead(BaseModel):
    id: int
    material_id: int
    codigo_lote: str
    cantidad: float
    cantidad_reservada: float
    cantidad_disponible: float
    almacen_id: Optional[int]
    locacion_id: Optional[int]
    costo_unitario: Optional[float]
    costo_total: Optional[float]
    fecha_entrada: datetime
    fecha_caducidad: Optional[datetime]
    notas: Optional[str]
    created_at: datetime

class MaterialLotUpdate(BaseModel):
    """Actualizar datos de lote (cantidad, ubicación, notas)"""
    cantidad: Optional[float] = Field(None, gt=0)
    almacen_id: Optional[int] = None
    locacion_id: Optional[int] = None
    notas: Optional[str] = None
    fecha_caducidad: Optional[datetime] = None

class MaterialInventorySummary(BaseModel):
    """Resumen del inventario de un material con stock total y lotes"""
    material_id: int
    codigo: str
    nombre: str
    unidad: str
    stock_total: float
    stock_disponible: float
    stock_reservado: float
    cantidad_lotes: int
    proximamente_caduca: int  # Lotes que caducan en próximos 30 días
    ya_caducados: int  # Lotes que ya pasaron fecha de caducidad
    lotes: list[MaterialLotRead]

class InventoryMovementRead(BaseModel):
    id: int
    inventory_type: str
    movement_type: str
    quantity: float
    material_id: Optional[int]
    material_lot_id: Optional[int]
    finished_product_id: Optional[int]
    work_order_id: Optional[int]
    user_id: Optional[int]
    user_name: Optional[str]
    reference_code: Optional[str]
    notes: Optional[str]
    unit_cost: Optional[float]
    total_cost: Optional[float]
    created_at: datetime
    model_config = {"from_attributes": True}

class InventoryMovementReportSummary(BaseModel):
    total_movements: int
    total_quantity: float
    entradas: float
    reservas: float
    consumos: float
    salidas: float
    ajustes: float
    model_config = {"from_attributes": True}

class InventoryMovementReportResponse(BaseModel):
    summary: InventoryMovementReportSummary
    movements: list[InventoryMovementRead]
    model_config = {"from_attributes": True}