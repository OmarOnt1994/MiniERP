"""add storage tables and lot location links

Revision ID: c4d5e6f7a8b9
Revises: b7c8d9e0f1a2
Create Date: 2026-05-17 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "almacen",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_almacen_codigo", "almacen", ["codigo"], unique=True)

    op.create_table(
        "locacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("almacen_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["almacen_id"], ["almacen.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("almacen_id", "codigo", name="uq_locacion_almacen_codigo"),
    )
    op.create_index("ix_locacion_almacen_id", "locacion", ["almacen_id"], unique=False)
    op.create_index("ix_locacion_codigo", "locacion", ["codigo"], unique=False)

    op.add_column("materiallot", sa.Column("almacen_id", sa.Integer(), nullable=True))
    op.add_column("materiallot", sa.Column("locacion_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_materiallot_almacen_id", "materiallot", "almacen", ["almacen_id"], ["id"])
    op.create_foreign_key("fk_materiallot_locacion_id", "materiallot", "locacion", ["locacion_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_materiallot_locacion_id", "materiallot", type_="foreignkey")
    op.drop_constraint("fk_materiallot_almacen_id", "materiallot", type_="foreignkey")
    op.drop_column("materiallot", "locacion_id")
    op.drop_column("materiallot", "almacen_id")

    op.drop_index("ix_locacion_codigo", table_name="locacion")
    op.drop_index("ix_locacion_almacen_id", table_name="locacion")
    op.drop_table("locacion")

    op.drop_index("ix_almacen_codigo", table_name="almacen")
    op.drop_table("almacen")
