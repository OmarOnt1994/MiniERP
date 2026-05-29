from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MaterialRequisitionItemCreate(BaseModel):
    material_id: int
    quantity: float = Field(gt=0)
    notes: Optional[str] = None


class MaterialRequisitionCreate(BaseModel):
    work_order_id: Optional[int] = None
    requester_area: Optional[str] = None
    purpose: Optional[str] = None
    is_secondary: bool = True
    notes: Optional[str] = None
    items: list[MaterialRequisitionItemCreate]


class MaterialRequisitionItemRead(BaseModel):
    id: int
    requisition_id: int
    material_id: int
    quantity: float
    delivered_quantity: float
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MaterialRequisitionRead(BaseModel):
    id: int
    codigo: str
    work_order_id: Optional[int]
    requester_area: Optional[str]
    purpose: Optional[str]
    is_secondary: bool
    status: str
    requested_by_user_id: Optional[int]
    approved_by_user_id: Optional[int]
    delivered_by_user_id: Optional[int]
    notes: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]
    delivered_at: Optional[datetime]
    items: list[MaterialRequisitionItemRead]


class MaterialRequisitionStatusUpdate(BaseModel):
    status: str
