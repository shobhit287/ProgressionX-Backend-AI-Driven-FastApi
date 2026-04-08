"""add_training_type_to_users

Revision ID: 18aadc33bfae
Revises: a1b2c3d4e5f6
Create Date: 2026-04-08 12:04:07.038644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '18aadc33bfae'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    training_type_enum = sa.Enum(
        'HYPERTROPHY', 'STRENGTH', 'POWERBUILDING', 'ENDURANCE', 'GENERAL_FITNESS',
        name='training_type_enum',
    )
    training_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'users',
        sa.Column(
            'training_type',
            training_type_enum,
            server_default='HYPERTROPHY',
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'training_type')
    sa.Enum(name='training_type_enum').drop(op.get_bind(), checkfirst=True)
