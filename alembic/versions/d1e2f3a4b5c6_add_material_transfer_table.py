"""add material transfer table

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-05-17 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materialtransfer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("source_lot_id", sa.Integer(), nullable=False),
        sa.Column("destination_lot_id", sa.Integer(), nullable=False),
        sa.Column("source_almacen_id", sa.Integer(), nullable=True),
        sa.Column("source_locacion_id", sa.Integer(), nullable=True),
        sa.Column("destination_almacen_id", sa.Integer(), nullable=True),
        sa.Column("destination_locacion_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_almacen_id"], ["almacen.id"]),
        sa.ForeignKeyConstraint(["destination_locacion_id"], ["locacion.id"]),
        sa.ForeignKeyConstraint(["destination_lot_id"], ["materiallot.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["material.id"]),
        sa.ForeignKeyConstraint(["source_almacen_id"], ["almacen.id"]),
        sa.ForeignKeyConstraint(["source_locacion_id"], ["locacion.id"]),
        sa.ForeignKeyConstraint(["source_lot_id"], ["materiallot.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materialtransfer_codigo", "materialtransfer", ["codigo"], unique=True)
    op.create_index("ix_materialtransfer_material_id", "materialtransfer", ["material_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_materialtransfer_material_id", table_name="materialtransfer")
    op.drop_index("ix_materialtransfer_codigo", table_name="materialtransfer")
    op.drop_table("materialtransfer")
