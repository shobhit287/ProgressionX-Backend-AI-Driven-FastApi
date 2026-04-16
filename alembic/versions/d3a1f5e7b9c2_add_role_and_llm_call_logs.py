"""add_role_to_users_and_llm_call_logs_table

Revision ID: d3a1f5e7b9c2
Revises: b9b8fbe23e1f
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3a1f5e7b9c2'
down_revision: Union[str, Sequence[str], None] = 'c4d7e9f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Add role enum type and column to users ---
    # Create the enum type first
    role_enum = sa.Enum('user', 'superadmin', name='role_enum')
    role_enum.create(op.get_bind(), checkfirst=True)

    # Add role column with server_default='user' so all existing rows
    # automatically get role='user' — no data loss, no nulls
    op.add_column(
        'users',
        sa.Column(
            'role',
            sa.Enum('user', 'superadmin', name='role_enum'),
            nullable=False,
            server_default='user',
        ),
    )

    # --- 2. Create llm_call_logs table ---
    op.create_table(
        'llm_call_logs',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('endpoint', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='success'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_llm_call_logs_created_at', 'llm_call_logs', ['created_at'])
    op.create_index('ix_llm_call_logs_user_id', 'llm_call_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_llm_call_logs_user_id', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_created_at', table_name='llm_call_logs')
    op.drop_table('llm_call_logs')

    op.drop_column('users', 'role')
    sa.Enum(name='role_enum').drop(op.get_bind(), checkfirst=True)
