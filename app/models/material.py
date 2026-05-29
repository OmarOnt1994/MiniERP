from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from datetime import datetime
from typing import Optional

class Material(SQLModel, table=True):
    """Maestro de materiales - define características del material"""
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    descripcion: Optional[str] = None
    unidad: str = "pieza"          # pieza, kg, litro, metro, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MaterialLot(SQLModel, table=True):
    """Lotes de material - registro por lote con FIFO y control de caducidad"""
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="material.id")
    codigo_lote: str = Field(index=True)  # Ej: "ACE-001-L001", "ACE-001-L002"
    cantidad: float = Field(gt=0, description="Cantidad disponible en el lote")
    cantidad_reservada: float = Field(default=0.0, ge=0)
    almacen_id: Optional[int] = Field(default=None, foreign_key="almacen.id")
    locacion_id: Optional[int] = Field(default=None, foreign_key="locacion.id")
    costo_unitario: Optional[float] = None
    costo_total: Optional[float] = None
    fecha_entrada: datetime = Field(default_factory=datetime.utcnow, index=True)
    fecha_caducidad: Optional[datetime] = None
    notas: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("material_id", "codigo_lote", name="uq_material_lote_codigo"),
    )

    @property
    def cantidad_disponible(self) -> float:
        return self.cantidad - self.cantidad_reservada

class InventoryMovement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_type: str = Field(index=True)  # material | finished_product
    movement_type: str = Field(index=True)    # entrada | reserva | consumo | salida | ajuste
    quantity: float = Field(gt=0)
    material_id: Optional[int] = Field(default=None, foreign_key="material.id")
    material_lot_id: Optional[int] = Field(default=None, foreign_key="materiallot.id")
    finished_product_id: Optional[int] = Field(default=None, foreign_key="finishedproduct.id")
    work_order_id: Optional[int] = Field(default=None, foreign_key="workorder.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    reference_code: Optional[str] = None
    notes: Optional[str] = None
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)