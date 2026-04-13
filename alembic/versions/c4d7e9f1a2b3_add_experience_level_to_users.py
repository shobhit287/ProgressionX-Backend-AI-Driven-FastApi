"""add_experience_level_to_users

Revision ID: c4d7e9f1a2b3
Revises: b9b8fbe23e1f
Create Date: 2026-04-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d7e9f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b9b8fbe23e1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    experience_level_enum = sa.Enum(
        'BEGINNER', 'INTERMEDIATE', 'ADVANCED',
        name='experience_level_enum',
    )
    experience_level_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'users',
        sa.Column(
            'experience_level',
            experience_level_enum,
            server_default='BEGINNER',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'experience_level')
    sa.Enum(name='experience_level_enum').drop(op.get_bind(), checkfirst=True)
