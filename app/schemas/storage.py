from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlmacenCreate(BaseModel):
    codigo: str
    nombre: str
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    activo: bool = True


class AlmacenRead(BaseModel):
    id: int
    codigo: str
    nombre: str
    tipo: Optional[str]
    descripcion: Optional[str]
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LocacionCreate(BaseModel):
    almacen_id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    activo: bool = True


class LocacionRead(BaseModel):
    id: int
    almacen_id: int
    codigo: str
    nombre: str
    descripcion: Optional[str]
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialTransferCreate(BaseModel):
    source_lot_id: int
    quantity: float
    destination_almacen_id: Optional[int] = None
    destination_locacion_id: Optional[int] = None
    destination_lot_code: Optional[str] = None
    notes: Optional[str] = None


class MaterialTransferRead(BaseModel):
    id: int
    codigo: str
    batch_id: Optional[int]
    material_id: int
    source_lot_id: int
    destination_lot_id: int
    source_almacen_id: Optional[int]
    source_locacion_id: Optional[int]
    destination_almacen_id: Optional[int]
    destination_locacion_id: Optional[int]
    quantity: float
    user_id: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialTransferBatchCreate(BaseModel):
    notes: Optional[str] = None
    items: list[MaterialTransferCreate]


class MaterialTransferBatchRead(BaseModel):
    id: int
    folio: str
    created_by_user_id: Optional[int]
    notes: Optional[str]
    item_count: int
    created_at: datetime
    items: list[MaterialTransferRead]

