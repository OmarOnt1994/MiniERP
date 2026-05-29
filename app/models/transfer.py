from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import sqlalchemy as sa


class MaterialTransferBatch(SQLModel, table=True):
    __tablename__ = "materialtransferbatch"

    id: Optional[int] = Field(default=None, primary_key=True)
    folio: str = Field(
        unique=True, 
        index=True, 
        sa_column_kwargs={"server_default": sa.text("'TF-' || LPAD(nextval('transfer_batch_folio_seq')::text, 6, '0')")}
    )
    created_by_user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    notes: Optional[str] = None
    item_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialTransfer(SQLModel, table=True):
    __tablename__ = "materialtransfer"

    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str = Field(
        unique=True, 
        index=True,
        sa_column_kwargs={"server_default": sa.text("'TR-' || LPAD(nextval('transfer_code_seq')::text, 6, '0')")}
    )
    batch_id: Optional[int] = Field(default=None, foreign_key="materialtransferbatch.id", index=True)
    material_id: int = Field(foreign_key="material.id", index=True)
    source_lot_id: int = Field(foreign_key="materiallot.id")
    destination_lot_id: int = Field(foreign_key="materiallot.id")
    source_almacen_id: Optional[int] = Field(default=None, foreign_key="almacen.id")
    source_locacion_id: Optional[int] = Field(default=None, foreign_key="locacion.id")
    destination_almacen_id: Optional[int] = Field(default=None, foreign_key="almacen.id")
    destination_locacion_id: Optional[int] = Field(default=None, foreign_key="locacion.id")
    quantity: float = Field(gt=0)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
