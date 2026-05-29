from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from datetime import datetime
from typing import Optional


class Almacen(SQLModel, table=True):
    __tablename__ = "almacen"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    nombre: str
    tipo: Optional[str] = None  # e.g. principal, secundarios, cuarentena
    descripcion: Optional[str] = None
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Locacion(SQLModel, table=True):
    __tablename__ = "locacion"

    id: Optional[int] = Field(default=None, primary_key=True)
    almacen_id: int = Field(foreign_key="almacen.id", index=True)
    codigo: str = Field(index=True)
    nombre: str
    descripcion: Optional[str] = None
    activo: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("almacen_id", "codigo", name="uq_locacion_almacen_codigo"),
    )
