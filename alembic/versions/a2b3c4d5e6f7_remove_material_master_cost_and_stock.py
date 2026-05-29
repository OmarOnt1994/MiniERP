"""remove material master cost and stock

Revision ID: a2b3c4d5e6f7
Revises: f7g8h9i0j1k2
Create Date: 2026-05-24 21:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f7g8h9i0j1k2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("material", "costo_unitario")
    op.drop_column("material", "stock_minimo")


def downgrade() -> None:
    op.add_column("material", sa.Column("stock_minimo", sa.Float(), nullable=False, server_default="0"))
    op.add_column("material", sa.Column("costo_unitario", sa.Float(), nullable=True))
    op.alter_column("material", "stock_minimo", server_default=None)
