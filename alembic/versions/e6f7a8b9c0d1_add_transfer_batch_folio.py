"""add transfer batch folio

Revision ID: e6f7a8b9c0d1
Revises: d1e2f3a4b5c6
Create Date: 2026-05-17 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materialtransferbatch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("folio", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materialtransferbatch_folio", "materialtransferbatch", ["folio"], unique=True)

    op.add_column("materialtransfer", sa.Column("batch_id", sa.Integer(), nullable=True))
    op.create_index("ix_materialtransfer_batch_id", "materialtransfer", ["batch_id"], unique=False)
    op.create_foreign_key(
        "fk_materialtransfer_batch_id",
        "materialtransfer",
        "materialtransferbatch",
        ["batch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_materialtransfer_batch_id", "materialtransfer", type_="foreignkey")
    op.drop_index("ix_materialtransfer_batch_id", table_name="materialtransfer")
    op.drop_column("materialtransfer", "batch_id")

    op.drop_index("ix_materialtransferbatch_folio", table_name="materialtransferbatch")
    op.drop_table("materialtransferbatch")
