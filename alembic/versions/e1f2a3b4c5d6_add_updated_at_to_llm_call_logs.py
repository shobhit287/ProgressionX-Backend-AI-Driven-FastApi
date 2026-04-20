"""add_updated_at_to_llm_call_logs

The original llm_call_logs migration (d3a1f5e7b9c2) created `created_at` but
omitted `updated_at`. LlmCallLog inherits from Base which defines both, so
every INSERT failed at the RETURNING step (`column updated_at does not
exist`). The failure was swallowed by the bare except in _log_llm_call so
the admin dashboard silently showed 0 LLM calls.

Revision ID: e1f2a3b4c5d6
Revises: d3a1f5e7b9c2
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd3a1f5e7b9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'llm_call_logs',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('llm_call_logs', 'updated_at')
