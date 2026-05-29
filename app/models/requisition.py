from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class MaterialRequisitionStatus(str, Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    entregada = "entregada"
    cancelada = "cancelada"


class MaterialRequisition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(unique=True, index=True)
    work_order_id: Optional[int] = Field(default=None, foreign_key="workorder.id")
    requester_area: Optional[str] = None
    purpose: Optional[str] = None
    is_secondary: bool = Field(default=True)
    status: MaterialRequisitionStatus = Field(default=MaterialRequisitionStatus.pendiente)
    requested_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    delivered_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class MaterialRequisitionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requisition_id: int = Field(foreign_key="materialrequisition.id")
    material_id: int = Field(foreign_key="material.id")
    quantity: float = Field(gt=0)
    delivered_quantity: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
