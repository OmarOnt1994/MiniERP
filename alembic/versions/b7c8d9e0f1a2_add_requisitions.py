"""add requisitions tables

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materialrequisition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=True),
        sa.Column("requester_area", sa.String(), nullable=True),
        sa.Column("purpose", sa.String(), nullable=True),
        sa.Column("is_secondary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("delivered_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["work_order_id"], ["workorder.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["delivered_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materialrequisition_codigo", "materialrequisition", ["codigo"], unique=True)

    op.create_table(
        "materialrequisitionitem",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requisition_id", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("delivered_quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["requisition_id"], ["materialrequisition.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["material.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("materialrequisitionitem")
    op.drop_index("ix_materialrequisition_codigo", table_name="materialrequisition")
    op.drop_table("materialrequisition")
