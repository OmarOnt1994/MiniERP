"""add transfer code sequences

Revision ID: f7g8h9i0j1k2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-17 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7g8h9i0j1k2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sequences for transfer codes
    op.execute("CREATE SEQUENCE transfer_code_seq START 1")
    op.execute("CREATE SEQUENCE transfer_batch_folio_seq START 1")
    
    # Add server_default to existing columns to use sequences
    op.alter_column(
        "materialtransfer",
        "codigo",
        existing_type=sa.String(),
        server_default=sa.text("'TR-' || LPAD(nextval('transfer_code_seq')::text, 6, '0')"),
        existing_nullable=False,
    )
    
    op.alter_column(
        "materialtransferbatch",
        "folio",
        existing_type=sa.String(),
        server_default=sa.text("'TF-' || LPAD(nextval('transfer_batch_folio_seq')::text, 6, '0')"),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Remove server defaults
    op.alter_column(
        "materialtransfer",
        "codigo",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )
    
    op.alter_column(
        "materialtransferbatch",
        "folio",
        existing_type=sa.String(),
        server_default=None,
        existing_nullable=False,
    )
    
    # Drop sequences
    op.execute("DROP SEQUENCE transfer_batch_folio_seq")
    op.execute("DROP SEQUENCE transfer_code_seq")
