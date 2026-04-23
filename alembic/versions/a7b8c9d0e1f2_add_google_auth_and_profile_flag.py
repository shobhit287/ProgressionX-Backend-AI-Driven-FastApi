"""add_google_auth_fields_and_profile_flag

Enables Google OAuth sign-in alongside existing email/password auth.

- Adds users.google_id (unique, nullable) — stores Google's `sub` claim for
  the primary match key on subsequent logins.
- Adds users.is_profile_complete (default true, server_default='true') —
  existing rows keep their current behavior; only stub Google users get
  false until they finish the fitness profile.
- Relaxes hashed_password to nullable so Google-only users can exist.
- Relaxes age/weight/height/goal/gender to nullable so stub users can be
  created before they complete the profile form. Training-type and
  experience-level already carry defaults so no change needed there.

Fully backward-compatible. All existing rows stay valid.

Revision ID: a7b8c9d0e1f2
Revises: f2a3b4c5d6e7
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New columns
    op.add_column(
        'users',
        sa.Column('google_id', sa.String(255), nullable=True),
    )
    op.create_index(
        'ix_users_google_id', 'users', ['google_id'], unique=True,
    )
    op.add_column(
        'users',
        sa.Column(
            'is_profile_complete',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
        ),
    )

    # Relax NOT NULL constraints. Existing rows aren't touched; the column
    # just now accepts NULL for future Google stubs.
    op.alter_column('users', 'hashed_password', nullable=True)
    op.alter_column('users', 'age', nullable=True)
    op.alter_column('users', 'weight', nullable=True)
    op.alter_column('users', 'height', nullable=True)
    op.alter_column('users', 'goal', nullable=True)
    op.alter_column('users', 'gender', nullable=True)


def downgrade() -> None:
    # Re-tightening nullability requires backfilling any NULLs first; this
    # downgrade assumes there are no Google-only users yet. If there are,
    # fix those rows manually before running downgrade.
    op.alter_column('users', 'gender', nullable=False)
    op.alter_column('users', 'goal', nullable=False)
    op.alter_column('users', 'height', nullable=False)
    op.alter_column('users', 'weight', nullable=False)
    op.alter_column('users', 'age', nullable=False)
    op.alter_column('users', 'hashed_password', nullable=False)

    op.drop_column('users', 'is_profile_complete')
    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_column('users', 'google_id')
