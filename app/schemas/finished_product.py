from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FinishedProductCreate(BaseModel):
    codigo: str
    lote_produccion: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    cantidad_producida: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    cantidad_disponible: Optional[float] = None
    costo_total: Optional[float] = None
    work_order_id: int

class FinishedProductRead(BaseModel):
    id: int
    codigo: str
    lote_produccion: str
    nombre: str
    descripcion: Optional[str]
    cantidad_producida: float
    cantidad_disponible: float
    costo_total: Optional[float]
    work_order_id: int
    created_at: datetime

class FinishedProductShipmentCreate(BaseModel):
    finished_product_id: int
    cantidad: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    destinatario: Optional[str] = None
    documento_envio: Optional[str] = None
    observaciones: Optional[str] = None

class FinishedProductShipmentRead(BaseModel):
    id: int
    finished_product_id: int
    cantidad: float
    destinatario: Optional[str]
    documento_envio: Optional[str]
    observaciones: Optional[str]
    created_at: datetime


class WorkOrderFinishedProductCreate(BaseModel):
    codigo: str
    lote_produccion: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    cantidad_producida: float = Field(gt=0, description="Cantidad debe ser mayor a 0")
    cantidad_disponible: Optional[float] = None
    costo_total: Optional[float] = None
