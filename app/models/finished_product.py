from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class FinishedProduct(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    lote_produccion: str = Field(index=True)
    nombre: str
    descripcion: Optional[str] = None
    cantidad_producida: float
    cantidad_disponible: float = Field(default=0.0, ge=0)
    costo_total: Optional[float] = None
    work_order_id: int = Field(foreign_key="workorder.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FinishedProductShipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    finished_product_id: int = Field(foreign_key="finishedproduct.id")
    cantidad: float = Field(gt=0)
    destinatario: Optional[str] = None
    documento_envio: Optional[str] = None
    observaciones: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
