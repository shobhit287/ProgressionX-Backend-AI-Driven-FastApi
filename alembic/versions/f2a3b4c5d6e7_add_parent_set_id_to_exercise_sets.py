"""add_parent_set_id_to_exercise_sets

Introduces parent_set_id on exercise_sets so dropsets can be linked to their
top set. Each drop row has parent_set_id=<top_set.id>; top sets stay NULL.
All existing rows stay NULL (behave as standalone sets) — no data rewrite.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exercise_sets',
        sa.Column('parent_set_id', sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_exercise_sets_parent_set_id',
        'exercise_sets',
        'exercise_sets',
        ['parent_set_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_exercise_sets_parent_set_id',
        'exercise_sets',
        ['parent_set_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_exercise_sets_parent_set_id', table_name='exercise_sets')
    op.drop_constraint(
        'fk_exercise_sets_parent_set_id', 'exercise_sets', type_='foreignkey'
    )
    op.drop_column('exercise_sets', 'parent_set_id')
