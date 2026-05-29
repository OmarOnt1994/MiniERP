from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: str
    role: str = Field(default="lectura")  # admin, almacen, produccion, despachos, lectura
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)