"""add_activity_level_to_users

Revision ID: 495fcbc220ee
Revises: 18aadc33bfae
Create Date: 2026-04-08 13:35:48.252339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '495fcbc220ee'
down_revision: Union[str, Sequence[str], None] = '18aadc33bfae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('activity_level', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'activity_level')
