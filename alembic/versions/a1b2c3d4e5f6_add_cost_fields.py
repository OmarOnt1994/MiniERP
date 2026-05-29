"""add cost fields to materiallot and inventorymovement

Revision ID: a1b2c3d4e5f6
Revises: dd7ff4170ded
Create Date: 2026-05-14 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dd7ff4170ded'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Añadir columnas de costo a materiallot
    op.add_column('materiallot', sa.Column('costo_unitario', sa.Float(), nullable=True))
    op.add_column('materiallot', sa.Column('costo_total', sa.Float(), nullable=True))

    # Añadir columnas de costo a inventorymovement
    op.add_column('inventorymovement', sa.Column('unit_cost', sa.Float(), nullable=True))
    op.add_column('inventorymovement', sa.Column('total_cost', sa.Float(), nullable=True))


def downgrade() -> None:
    # Quitar columnas de inventorymovement
    op.drop_column('inventorymovement', 'total_cost')
    op.drop_column('inventorymovement', 'unit_cost')

    # Quitar columnas de materiallot
    op.drop_column('materiallot', 'costo_total')
    op.drop_column('materiallot', 'costo_unitario')
